# Модуль 12: Анализ настроений (Sentiment Analysis)

## Обзор

Sentiment analysis превращает «голос рынка» — соцсети, новости, поисковые запросы — в числовую метрику, которую бот может использовать как фильтр или подтверждающий сигнал. В отличие от технических индикаторов (цена, объём), sentiment — это **вторичный сигнал**: он отражает намерения и эмоции участников, которые ещё не реализовались в цене.

### Философия модуля

Sentiment — это **приправа, а не основное блюдо**. Он не заменяет ценовые индикаторы, а даёт дополнительный контекст. Бот использует sentiment как:
1. **Фильтр уверенности** (confidence filter): sentiment подтверждает → размер позиции ×1.2, противоречит → ×0.5.
2. **Contrarian extreme detector**: экстремальные значения → разворотный сигнал.
3. **Предупреждение о волатильности**: резкий spike sentiment → готовься к движению.

---

## Полный аудит источников настроений

### 1. Crypto Fear & Greed Index

| Параметр | Значение |
|---|---|
| **Источник** | alternative.me/fear-and-greed-index |
| **Метод сбора** | GET `https://api.alternative.me/fng/?limit=N` |
| **Частота обновления** | Каждые 24 часа (daily) |
| **Диапазон** | 0 (Extreme Fear) — 100 (Extreme Greed) |

#### Что входит в индекс

Alternative.me комбинирует 6 компонентов:
1. **Volatility (25%)**: текущая волатильность vs 30/90/252-дневная. Аномально высокая → fear.
2. **Market Momentum/Volume (25%)**: текущий объём vs средний. Высокий объём на растущем рынке → greed.
3. **Social Media (15%)**: Reddit, Twitter hashtag-анализ (упрощённый NLP).
4. **Surveys (15%)**: опросы на strawpoll.com (на практике почти всегда пустые → вес перераспределяется).
5. **Dominance (10%)**: BTC dominance. Растущий dominance = fear (бегство в «безопасный» BTC).
6. **Trends (10%)**: Google Trends для Bitcoin.

#### Формула обработки

```
// Нормализация в диапазон [-1, 1] для бота
sentiment_fng = (fng_value - 50) / 50.0

// Extreme zones
extreme_fear  = fng_value < 20
extreme_greed = fng_value > 80
```

#### Edge Cases
- **API может не обновляться сутки**: кэшировать на 24ч, не спамить.
- **Surveys component = 0**: вес перераспределяется на остальные 5 компонентов.
- **BTC dominance введёт в заблуждение** в альткоин-сезон: dominance падает, но это greed для альтов, а не fear.
- **Одна точка в день** — слишком мало для 1H стратегии. Используется только как дневной контекст.

#### Rust-реализация

```rust
use serde::Deserialize;
use chrono::{DateTime, Utc};

#[derive(Debug, Deserialize)]
struct FngResponse {
    data: Vec<FngDataPoint>,
}

#[derive(Debug, Deserialize)]
struct FngDataPoint {
    value: String,
    value_classification: String,
    timestamp: String,
}

#[derive(Debug, Clone)]
pub struct FearGreedSignal {
    pub raw_value: f64,          // 0..100
    pub normalized: f64,         // -1..1
    pub classification: FngClass,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, PartialEq)]
pub enum FngClass {
    ExtremeFear,
    Fear,
    Neutral,
    Greed,
    ExtremeGreed,
}

impl FngClass {
    fn from_value(v: f64) -> Self {
        match v {
            v if v < 20.0 => FngClass::ExtremeFear,
            v if v < 40.0 => FngClass::Fear,
            v if v < 60.0 => FngClass::Neutral,
            v if v < 80.0 => FngClass::Greed,
            _ => FngClass::ExtremeGreed,
        }
    }
}

pub fn parse_fng_response(body: &str) -> Result<FearGreedSignal, Box<dyn std::error::Error>> {
    let resp: FngResponse = serde_json::from_str(body)?;
    let latest = resp.data.first().ok_or("empty FNG data")?;
    let raw: f64 = latest.value.parse()?;
    Ok(FearGreedSignal {
        raw_value: raw,
        normalized: (raw - 50.0) / 50.0,
        classification: FngClass::from_value(raw),
        timestamp: DateTime::from_timestamp(latest.timestamp.parse::<i64>()?, 0)
            .unwrap_or_else(Utc::now),
    })
}

/// Contrarian логика: extreme fear = потенциальный buy, extreme greed = потенциальный sell
pub fn contrarian_weight(fng: &FearGreedSignal) -> f64 {
    match fng.classification {
        FngClass::ExtremeFear => 0.8,   // сильный contrarian buy-сигнал
        FngClass::Fear => 0.3,
        FngClass::Neutral => 0.0,
        FngClass::Greed => -0.3,
        FngClass::ExtremeGreed => -0.8, // сильный contrarian sell-сигнал
    }
}
```

---

### 2. Twitter/X Sentiment

| Параметр | Значение |
|---|---|
| **Источник** | Twitter API v2 (Academic Research или Basic) |
| **Метод сбора** | GET `2/tweets/search/recent` с фильтрами по crypto-хештегам |
| **Частота** | Каждые 15 минут (rate limit: 450/15min для App-only) |
| **Объём** | ~50-200 твитов за запрос |

#### Метод сбора

```
Query: "bitcoin OR btc OR ethereum OR eth OR #crypto -is:retweet lang:en"
Max results: 100 per request
Fields: created_at, public_metrics, text, author_id
```

#### NLP-обработка

Два варианта:
1. **VADER (lexicon-based)**: быстрый, но поверхностный. Хорош для сарказма в английском.
2. **Fine-tuned transformer** (например, `cardiffnlp/twitter-roberta-base-sentiment`): точнее, но тяжелее.

**Формула:**
```
// VADER: compound score [-1, 1]
vader_score = vader_analyzer(twt.text)

// Учёт ретвитов и лайков (взвешенный сентимент)
engagement = likes + 2 * retweets + 0.5 * replies
weighted_sentiment = Σ(vader_score_i * engagement_i) / Σ(engagement_i)

// Сглаживание EMA с периодом 12 (3 часа при 15мин обновлении)
smoothed_sentiment = EMA(weighted_sentiment, period=12)
```

#### Edge Cases
- **Боты** — 30-50% крипто-твитов генерируются ботами. Фильтр: account age > 30 дней, followers > 50, не retweet-only.
- **Манипуляции pump groups**: координированные твиты → spike sentiment без реальной причины.
- **Elon Musk effect**: один твит может сдвинуть sentiment на 2σ. Нужен outlier detector.
- **Rate limit**: Twitter API платный ($100/mo Basic), Academic ($500/mo) даёт полный доступ.
- **Многоязычность**: русскоязычные, китайскоязычные каналы часто игнорируются.
- **Кэширование**: твиты не меняются после публикации, но sentiment-оценка может меняться при обновлении модели NLP.

#### Rust-реализация

```rust
use reqwest::Client;
use serde::Deserialize;

#[derive(Debug, Deserialize)]
struct TweetSearchResponse {
    data: Option<Vec<Tweet>>,
    meta: TweetMeta,
}

#[derive(Debug, Deserialize)]
struct Tweet {
    id: String,
    text: String,
    created_at: String,
    public_metrics: TweetMetrics,
    author_id: String,
}

#[derive(Debug, Deserialize)]
struct TweetMetrics {
    like_count: u64,
    retweet_count: u64,
    reply_count: u64,
}

#[derive(Debug, Deserialize)]
struct TweetMeta {
    result_count: u64,
    next_token: Option<String>,
}

#[derive(Debug, Clone)]
pub struct TwitterSentiment {
    pub weighted_score: f64,     // -1..1
    pub smoothed: f64,           // EMA-сглаженный
    pub sample_size: usize,
    pub bot_ratio: f64,          // доля подозрительных аккаунтов
}

pub struct TwitterCollector {
    client: Client,
    bearer_token: String,
    bot_filter: BotDetector,
    ema: EmaFilter,
}

impl TwitterCollector {
    pub async fn collect(&self, query: &str) -> Result<TwitterSentiment, Box<dyn std::error::Error>> {
        let resp: TweetSearchResponse = self.client
            .get("https://api.twitter.com/2/tweets/search/recent")
            .bearer_auth(&self.bearer_token)
            .query(&[
                ("query", query),
                ("max_results", "100"),
                ("tweet.fields", "created_at,public_metrics,author_id"),
            ])
            .send()
            .await?
            .json()
            .await?;

        let tweets = resp.data.unwrap_or_default();
        let total = tweets.len();
        let mut bot_count = 0usize;
        let mut weighted_sum = 0.0f64;
        let mut weight_total = 0.0f64;

        for tweet in &tweets {
            if self.bot_filter.is_bot(tweet) {
                bot_count += 1;
                continue;
            }
            let sentiment = vader_sentiment(&tweet.text);
            let engagement = tweet.public_metrics.like_count as f64
                + 2.0 * tweet.public_metrics.retweet_count as f64
                + 0.5 * tweet.public_metrics.reply_count as f64;
            let w = engagement.max(1.0); // минимум 1, чтобы учесть все твиты
            weighted_sum += sentiment * w;
            weight_total += w;
        }

        let weighted_score = if weight_total > 0.0 { weighted_sum / weight_total } else { 0.0 };
        let smoothed = self.ema.update(weighted_score);

        Ok(TwitterSentiment {
            weighted_score,
            smoothed,
            sample_size: total,
            bot_ratio: if total > 0 { bot_count as f64 / total as f64 } else { 0.0 },
        })
    }
}
```

---

### 3. Reddit Sentiment

| Параметр | Значение |
|---|---|
| **Источник** | Reddit API (OAuth2) / Pushshift (исторические данные) |
| **Subreddits** | r/CryptoCurrency, r/Bitcoin, r/ethereum, r/CryptoMarkets |
| **Частота** | Каждые 30 минут |
| **Объём** | ~100-500 постов + комментарии |

#### Метод сбора

```
GET /r/CryptoCurrency/hot?limit=100
GET /r/CryptoCurrency/comments/{post_id}?limit=200
```

#### Формула обработки

```
// Для каждого поста:
post_sentiment = NLP(post.title + post.selftext)
comment_sentiment = avg(NLP(comment.body) for comment in comments)

// Upvote-weighted:
upvote_weight = log(1 + score)   // логарифмическое сглаживание
weighted_post_sentiment = post_sentiment * upvote_weight

// Комментарии: по 1/top-level, не по количеству
top_level_sentiment = median(NLP(c) for c in top_level_comments)
// Используем median, а не mean, чтобы убрать extreme shitposting

// Итого:
reddit_sentiment = 0.4 * weighted_post_sentiment + 0.6 * top_level_sentiment
```

#### Edge Cases
- **Reddit upvote manipulation**: vote fuzzing + боты-апвоутеры. Score ненадёжен на новых постах.
- **Echo chamber effect**: r/CryptoCurrency = perma-bull, r/Bitcoin = perma-maxi. Sentiment всегда смещён вверх.
- **Shitposting / memes**: "🚀🚀🚀 TO THE MOON" — не настоящий сентимент, а культурный феномен.
- **Comment depth**: ответы на 5-м уровне часто — споры без ценности. Ограничивать depth ≤ 3.
- **Sarcasm**: Reddit полон сарказма ("Great, another -20% day, love crypto"). NLP часто ошибается.

#### Rust-реализация

```rust
#[derive(Debug)]
pub struct RedditSentiment {
    pub hot_posts_score: f64,
    pub comment_score: f64,
    pub combined: f64,
    pub post_count: usize,
    pub comment_count: usize,
}

pub struct RedditCollector {
    client: Client,
    access_token: String,
    subreddits: Vec<String>,
}

impl RedditCollector {
    pub async fn collect(&self) -> Result<RedditSentiment, Box<dyn std::error::Error>> {
        let mut post_sentiments = Vec::new();
        let mut comment_sentiments = Vec::new();

        for sub in &self.subreddits {
            // Hot posts
            let posts: RedditListing = self.client
                .get(&format!("https://oauth.reddit.com/{}/hot", sub))
                .bearer_auth(&self.access_token)
                .query(&[("limit", "100")])
                .send().await?.json().await?;

            for post in &posts.data.children {
                let text = format!("{} {}", post.data.title, post.data.selftext);
                let raw_sentiment = analyze_sentiment(&text);
                let weight = (1.0 + post.data.score as f64).ln().max(1.0);
                post_sentiments.push(raw_sentiment * weight);

                // Top-level comments
                let comments = self.fetch_comments(&post.data.id, 50).await?;
                for c in comments {
                    if c.depth == 0 {
                        comment_sentiments.push(analyze_sentiment(&c.body));
                    }
                }
            }
        }

        let hot_posts_score = median(&post_sentiments).unwrap_or(0.0);
        let comment_score = median(&comment_sentiments).unwrap_or(0.0);
        let combined = 0.4 * hot_posts_score + 0.6 * comment_score;

        Ok(RedditSentiment {
            hot_posts_score,
            comment_score,
            combined,
            post_count: post_sentiments.len(),
            comment_count: comment_sentiments.len(),
        })
    }
}
```

---

### 4. Google Trends

| Параметр | Значение |
|---|---|
| **Источник** | Pytrends (неофициальный Python-клиент для Google Trends) |
| **Для Rust** | Scrape через `reqwest` + парсинг JSON endpoint |
| **Частота** | Каждые 4 часа (realtime hourly data доступно) |
| **Масштаб** | Относительный: 0-100 (100 = пик популярности) |

#### Формула обработки

```
// Запросы: "buy bitcoin", "bitcoin price", "crypto crash", "bitcoin dead"
// Используем комбинацию bull и bear ключевых слов

bull_queries = ["buy bitcoin", "bitcoin price", "crypto bull run"]
bear_queries = ["crypto crash", "bitcoin dead", "sell bitcoin"]

bull_trend = avg(google_trends(q) for q in bear_queries)  // 0..100
bear_trend = avg(google_trends(q) for q in bear_queries)  // 0..100

// Нормализация
google_sentiment = (bull_trend - bear_trend) / 100.0  // -1..1

// Rate of change (важнее абсолютного значения)
trend_velocity = (current - previous_4h) / previous_4h
// sudden spike in "crypto crash" queries = предупреждение
```

#### Edge Cases
- **Relative scale**: 100 не означает «много», а «максимум за период». Тренд 70 в 2024 ≠ тренд 70 в 2021.
- **Noisy keywords**: "bitcoin" может означать и инвестиции, и технологии, и новости.
- **Seasonal patterns**: тренды растут по праздникам и в начале года (New Year resolutions).
- **Language bias**: Google Trends преимущественно англоязычный. Китайские тренды = Baidu Index (отдельный источник).
- **Lag**: Google Trends имеет задержку ~2-4 часа относительно реальных событий.

#### Rust-реализация

```rust
pub struct GoogleTrendsCollector {
    client: Client,
    bull_keywords: Vec<String>,
    bear_keywords: Vec<String>,
}

#[derive(Debug, Clone)]
pub struct GoogleTrendsSignal {
    pub bull_score: f64,
    pub bear_score: f64,
    pub sentiment: f64,        // -1..1
    pub velocity: f64,         // rate of change
    pub spike_detected: bool,
}

impl GoogleTrendsCollector {
    pub async fn collect(&self) -> Result<GoogleTrendsSignal, Box<dyn std::error::Error>> {
        let bull_score = self.avg_trend(&self.bull_keywords).await?;
        let bear_score = self.avg_trend(&self.bear_keywords).await?;

        let sentiment = (bull_score - bear_score) / 100.0;

        // Velocity: сравнение с предыдущим значением из кэша
        let prev = self.load_previous().await.unwrap_or(sentiment);
        let velocity = if prev.abs() > 0.01 { (sentiment - prev) / prev } else { 0.0 };
        let spike_detected = velocity.abs() > 0.5; // 50% изменение за 4 часа

        self.save_current(sentiment).await?;

        Ok(GoogleTrendsSignal {
            bull_score,
            bear_score,
            sentiment,
            velocity,
            spike_detected,
        })
    }

    async fn avg_trend(&self, keywords: &[String]) -> Result<f64, Box<dyn std::error::Error>> {
        let mut total = 0.0;
        for kw in keywords {
            // Google Trends JSON endpoint (неофициальный, может сломаться)
            let resp = self.client
                .get("https://trends.google.com/trends/api/widgetdata/comparedgeo")
                .query(&[("req", format!(r#"{{"keyword":"{}","time":"now 4-H"}}"#, kw))])
                .send().await?.text().await?;
            total += self.parse_trend_value(&resp)?;
        }
        Ok(total / keywords.len() as f64)
    }
}
```

---

### 5. News Sentiment (NLP)

| Параметр | Значение |
|---|---|
| **Источник** | NewsAPI, CryptoPanic, CoinTelegraph RSS, CoinDesk RSS |
| **Метод** | RSS aggregation + NLP classification |
| **Частота** | Каждые 30 минут |
| **Объём** | ~50-200 заголовков за цикл |

#### Формула обработки

```
// Шаг 1: Сбор заголовков
headlines = collect_from_sources(["cryptopanic", "cointelegraph", "coindesk", "newsapi"])

// Шаг 2: Классификация
// CryptoPanic уже даёт sentiment: positive/negative/neutral/important
// Для остальных — NLP

for headline in headlines:
    if headline.source == "cryptopanic":
        score = cryptopanic_sentiment_map(headline.sentiment)  // их разметка
    else:
        score = transformer_sentiment(headline.title + headline.description)

// Шаг 3: Свежесть (recency weight)
age_hours = (now - headline.published_at).hours
freshness_weight = exp(-age_hours / 24.0)  // экспоненциальный decay

// Шаг 4: Источник-вес
source_weight = match source {
    "coindesk" => 1.2,       // авторитетный
    "cointelegraph" => 1.0,
    "cryptopanic" => 0.8,    // агрегатор, качество варьируется
    _ => 0.6,
}

// Итого
news_sentiment = Σ(score_i * freshness_i * source_i) / Σ(freshness_i * source_i)
```

#### Edge Cases
- **Recycled news**: один и тот же контент репостится 10+ раз. Dedup по заголовку (simhash).
- **Opinion vs fact**: editorial («Bitcoin to $1M») ≠ factual («SEC approves ETF»). Разные веса.
- **Breaking news lag**: важные новости появляются в Twitter раньше, чем в СМИ.
- **Paid articles / sponsored**: CoinTelegraph публикует sponsored content. Фильтр по меткам.
- **Translation artifacts**: китайские новости, переведённые на английский, теряют нюансы.

#### Rust-реализация

```rust
use chrono::{Duration, Utc};
use std::collections::HashMap;

#[derive(Debug)]
struct NewsItem {
    title: String,
    description: String,
    source: String,
    published_at: DateTime<Utc>,
    tags: Vec<String>,  // от CryptoPanic: ["positive", "negative", "important"]
}

#[derive(Debug, Clone)]
pub struct NewsSentimentSignal {
    pub score: f64,
    pub article_count: usize,
    pub important_ratio: f64,  // доля "important" новостей
}

pub struct NewsCollector {
    sources: Vec<Box<dyn NewsSource>>,
    dedup_cache: SimhashCache,
    transformer: SentimentModel,
}

impl NewsCollector {
    pub async fn collect(&self) -> Result<NewsSentimentSignal, Box<dyn std::error::Error>> {
        let mut items = Vec::new();
        for source in &self.sources {
            items.extend(source.fetch().await?);
        }

        // Dedup
        items.retain(|item| {
            let hash = simhash(&item.title);
            !self.dedup_cache.contains(hash)
        });

        let now = Utc::now();
        let mut weighted_sum = 0.0;
        let mut weight_total = 0.0;
        let mut important_count = 0;

        for item in &items {
            let score = if item.source == "cryptopanic" {
                cp_sentiment(&item.tags)
            } else {
                self.transformer.predict(&format!("{} {}", item.title, item.description))
            };

            let age_hours = (now - item.published_at).num_hours() as f64;
            let freshness = (-age_hours / 24.0).exp();
            let source_w = source_weight(&item.source);
            let w = freshness * source_w;

            weighted_sum += score * w;
            weight_total += w;

            if item.tags.contains(&"important".to_string()) {
                important_count += 1;
            }
        }

        Ok(NewsSentimentSignal {
            score: if weight_total > 0.0 { weighted_sum / weight_total } else { 0.0 },
            article_count: items.len(),
            important_ratio: if items.len() > 0 {
                important_count as f64 / items.len() as f64
            } else { 0.0 },
        })
    }
}

fn source_weight(source: &str) -> f64 {
    match source {
        "coindesk" => 1.2,
        "cointelegraph" => 1.0,
        "cryptopanic" => 0.8,
        "reuters" | "bloomberg" => 1.5,  // мейнстрим = крупные движения
        _ => 0.6,
    }
}
```

---

### 6. Telegram Groups Sentiment

| Параметр | Значение |
|---|---|
| **Источник** | Telegram Bot API (чтение сообщений из публичных групп) |
| **Частота** | Каждые 15 минут |
| **Группы** | Топ крипто-чаты (100K+ участников) |

#### Метод сбора

```
// Через Telegram Bot API (нужен бот в группе)
// Альтернатива: Telethon (userbot) — риск бана

GET /getUpdates → messages from groups
```

#### Формула обработки

```
// Проблема: Telegram — это шум. 90% сообщений = "gm", "lfg", стикеры, ссылки.
// Фильтрация:
filtered_messages = messages.filter(|m| m.text.len() > 20 && !is_sticker(m) && !is_spam(m))

// Sentiment через быстрый lexicon-based подход (transformers слишком медленны)
telegram_sentiment = vader_or_lexicon(avg(filtered_messages))

// Учёт активности (не сентимента)
activity_score = message_count_now / avg_message_count_24h
// Spike в активности = что-то происходит (независимо от направления)
```

#### Edge Cases
- **Extreme noise**: Telegram-чаты = помойка. 80% = мусор.
- **Scam bots**: фейковые «поддержка», «airdrop» сообщения.
- **Культурный bias**: русскоязычные чаты (особенно каналы «сигналов») — pump/dump.
- **Privacy concerns**: Telegram API имеет ограничения на чтение. Userbot = риск бана аккаунта.
- **Language mix**: один чат может содержать 5+ языков.

#### Оценка: **НЕ рекомендуется для MVP**

Telegram sentiment — это 20% сигнала на 80% усилий. Noise-to-signal ratio слишком плохой. Версия v0.5+ если нужен.

#### Rust-реализация (упрощённая)

```rust
pub struct TelegramCollector {
    bot_token: String,
    group_ids: Vec<i64>,
    spam_filter: SpamDetector,
}

#[derive(Debug)]
pub struct TelegramSignal {
    pub sentiment: f64,
    pub activity_ratio: f64,   // текущая vs средняя активность
    pub message_count: usize,
    pub spam_ratio: f64,
}

impl TelegramCollector {
    pub async fn collect(&self) -> Result<TelegramSignal, Box<dyn std::error::Error>> {
        let mut sentiments = Vec::new();
        let mut total = 0usize;
        let mut spam_count = 0usize;

        for group_id in &self.group_ids {
            let messages = self.fetch_recent_messages(*group_id, 200).await?;
            for msg in &messages {
                total += 1;
                if msg.text.len() < 20 || self.spam_filter.is_spam(msg) {
                    spam_count += 1;
                    continue;
                }
                sentiments.push(lexicon_sentiment(&msg.text));
            }
        }

        let avg_sentiment = sentiments.iter().sum::<f64>() / sentiments.len().max(1) as f64;
        let activity = self.compute_activity_ratio(total).await?;

        Ok(TelegramSignal {
            sentiment: avg_sentiment,
            activity_ratio: activity,
            message_count: total,
            spam_ratio: if total > 0 { spam_count as f64 / total as f64 } else { 0.0 },
        })
    }
}
```

---

### 7. GitHub Commits / Development Activity

| Параметр | Значение |
|---|---|
| **Источник** | GitHub API, Santiment, CryptoMiso |
| **Метод** | Подсчёт коммитов, PR, issues за период |
| **Частота** | Каждые 6 часов |

#### Что это даёт

Development activity ≠ price sentiment. Это **фундаментальный** индикатор, не сентимент. Но он косвенно отражает доверие к проекту:
- ↑ commits = команда работает → долгосрочный bullish фундамент
- ↓ commits = проект может умирать → bearish
- Spike в PR/issues = активное обсуждение (возможен релиз → catalyst)

#### Формула

```
// Для топ-20 альткоинов (по market cap)
for project in top_projects:
    commits_30d = github_commits(project.repo, days=30)
    commits_prev = github_commits(project.repo, days=30, offset=30)
    dev_momentum = (commits_30d - commits_prev) / max(commits_prev, 1)

// Агрегация
dev_sentiment = median(dev_momentum for all projects)
// Median, не mean: один мёртвый проект не должен тянуть вниз

// Нормализация
dev_sentiment_norm = tanh(dev_sentiment)  // -1..1 через tanh
```

#### Edge Cases
- **Monorepo vs small repo**: Bitcoin Core — десятки тысяч строк, один commit = огромный объём. Маленький альт — 10 коммитов = косметические правки.
- **Bot commits**: Dependabot, Renovate генерируют автоматические обновления.
- **Branch strategies**: squash merge = 1 коммит за PR, но содержит 20 реальных изменений.
- **Not price-predictive**: development activity опережает цену на месяцы, не часы.

#### Оценка: **Полезен, но НЕ для трейдингового сентимента**

Development activity — это фундаментальный индикатор. Используется в фундаментальном модуле (если будет), а не в sentiment.

---

### 8. Social Volume & Social Dominance

| Параметр | Значение |
|---|---|
| **Источник** | LunarCrush, Santiment (Sanbase) |
| **Частота** | Каждые 1-4 часа |
| **Стоимость** | API платный ($50-500/месяц) |

#### Что это

- **Social Volume**: общее количество упоминаний криптовалюты в соцсетях (Twitter, Reddit, Telegram, Bitcointalk, YouTube).
- **Social Dominance**: social volume монеты / social volume всего крипто-рынка.

#### Формула

```
social_volume_now = lunarcrush.social_volume(symbol)
social_volume_avg = SMA(social_volume, period=30)  // 30-дневная средняя

volume_spike = social_volume_now / social_volume_avg
// volume_spike > 2.0 = аномально высокий интерес → catalyst

social_dominance_now = lunarcrush.social_dominance(symbol)
social_dominance_prev = social_dominance(yesterday)

dominance_change = social_dominance_now - social_dominance_prev
// dominance растёт → ассет привлекает внимание (bullish или bearish зависит от контекста)
```

#### Edge Cases
- **Correlation with price**: social volume почти всегда коррелирует с ценой (следствие, а не причина). Прогнозная ценность низкая.
- **Whale manipulation**: крупные игроки могут создавать buzz через оплаченных инфлюенсеров.
- **API cost**: LunarCrush $50/mo, Santiment от $50/mo. Для MVP — дороговато.
- **Token-level granularity**: работает для топ-100 монет, но для новых/малых — данных нет.

#### Оценка: **Полезен как spike detector, не как регулярный сентимент**

Social volume spike > 2σ = «что-то происходит». Направление движения определяется другими индикаторами.

---

### 9. Funding Rate (как сентимент)

| Параметр | Значение |
|---|---|
| **Источник** | Биржевые API (Binance, Bybit, OKX) |
| **Частота** | Каждые 8 часов (при смене funding) |
| **Диапазон** | Обычно -0.05% .. +0.05% |

#### Почему это сентимент

Funding rate отражает **позиционирование трейдеров**:
- Положительный funding = longs платят shorts → быки агрессивны → перекупленность → contrarian short
- Отрицательный funding = shorts платят longs → медведи агрессивны → перепроданность → contrarian long

Это **один из лучших сентимент-индикаторов** для крипты, потому что отражает реальные деньги, а не слова.

#### Формула

```
funding_rate = exchange.get_funding_rate(symbol)  // 0.01% = 0.0001

// Нормализация
funding_norm = funding_rate / 0.01  // 0.01% = нормальный funding, нормализуем к 1.0

// Contrarian signal
funding_sentiment = -tanh(funding_norm * 10)  // высокий funding → отрицательный сентимент

// Extreme detection
extreme_long = funding_rate > 0.05%   // перекупленность
extreme_short = funding_rate < -0.05%  // перепроданность
```

#### Edge Cases
- **Нормальный funding**: на BTC/USDT funding часто положительный (long bias рынка). Это нормально, не сигнал.
- **Funding spikes**: перед крупными движениями funding может улетать на 0.1%+ за часы до пампа/дампа.
- **Exchange差异**: funding на Binance и Bybit может отличаться на 0.01-0.02%. Нужно брать среднее.
- **Время смены funding**: 00:00, 08:00, 16:00 UTC. Spike часто происходит прямо перед сменой.

#### Оценка: **ТОП-1 для сентимента по крипто-деривативам**

#### Rust-реализация

```rust
use std::collections::VecDeque;

#[derive(Debug, Clone)]
pub struct FundingSentiment {
    pub current_rate: f64,
    pub normalized: f64,
    pub sentiment: f64,          // -1..1 (contrarian)
    pub is_extreme: bool,
    pub rolling_avg_7d: f64,
}

pub struct FundingCollector {
    exchanges: Vec<Box<dyn FundingProvider>>,
    history: VecDeque<f64>,
    max_history: usize,          // 21 (7 дней × 3 смены/день)
}

impl FundingCollector {
    pub async fn collect(&mut self, symbol: &str) -> Result<FundingSentiment, Box<dyn std::error::Error>> {
        // Средний funding по биржам
        let mut rates = Vec::new();
        for exchange in &self.exchanges {
            if let Ok(rate) = exchange.get_funding_rate(symbol).await {
                rates.push(rate);
            }
        }
        let avg_rate = rates.iter().sum::<f64>() / rates.len().max(1) as f64;

        // Обновляем историю
        self.history.push_back(avg_rate);
        if self.history.len() > self.max_history {
            self.history.pop_front();
        }

        let rolling_avg = self.history.iter().sum::<f64>() / self.history.len() as f64;
        let normalized = avg_rate / 0.0001; // 0.01% = базовый уровень
        let sentiment = -(normalized * 10.0).tanh(); // contrarian: высокий funding = bearish
        let is_extreme = avg_rate.abs() > 0.0005; // 0.05%

        Ok(FundingSentiment {
            current_rate: avg_rate,
            normalized,
            sentiment,
            is_extreme,
            rolling_avg_7d: rolling_avg,
        })
    }
}
```

---

### 10. Long/Short Ratio

| Параметр | Значение |
|---|---|
| **Источник** | Binance, Bybit, OKX API |
| **Частота** | Каждые 15 минут |
| **Диапазон** | 0.5 .. 2.0 (typical) |

#### Формула

```
long_short_ratio = total_long_positions / total_short_positions

// Sentiment: contrarian
lsr_sentiment = -tanh((lsr - 1.0) * 5)
// ratio > 1.5 → перекупленность → contrarian bearish
// ratio < 0.7 → перепроданность → contrarian bullish
```

#### Оценка: **Хороший дополнительный сентимент-индикатор, easy to implement**

---

### 11. Exchange Inflow/Outflow

| Параметр | Значение |
|---|---|
| **Источник** | Glassnode, CryptoQuant, Whale Alert |
| **Частота** | Каждый блок / каждый час |
| **Стоимость** | $29-800/месяц (Glassnode) |

#### Логика
- BTC inflow to exchanges → intent to sell → bearish
- BTC outflow from exchanges → intent to hold → bullish

#### Оценка: **Хороший on-chain сентимент, но дорогие API. v0.3+.**

---

### 12. Stablecoin Supply Ratio (SSR)

| Формула | Значение |
|---|---|
| SSR = BTC Market Cap / Stablecoin Market Cap | Чем ниже SSR → тем больше «сухого пороха» → bullish потенциал |

#### Оценка: **Интересный macro-индикатор, не сентимент в классическом смысле. v0.3+.**

---

## Contrarian vs Follower: когда что работает

### Sentiment как Contrarian индикатор

**Принцип**: «Buy when there's blood in the streets» — когда все в панике, рынок близок к дну.

**Когда работает**:
- **Extreme Fear & Greed** (F&G < 15 или > 85): исторически, покупка в extreme fear и продажа в extreme greed даёт положительный excess return на горизонте 30-90 дней.
- **Extreme funding rates**: funding > 0.1% или < -0.1% предшествует развороту в 65-70% случаев (эмпирически).
- **L/S ratio extremes**: когда 80%+ трейдеров в long → кто-то должен будет продать для фиксации.

**Когда НЕ работает**:
- В сильном тренде (BTC от $10K до $60K в 2020-2021): extreme greed держался месяцами. Contrarian short = банкротство.
- During black swan: Terra/Luna, FTX collapse. Extreme fear → ещё более extreme fear.

### Sentiment как Follower (подтверждающий) индикатор

**Принцип**: Sentiment подтверждает то, что уже показывают ценовые индикаторы.

**Когда работает**:
- **Sentiment + Trend alignment**: EMA bullish cross + positive news sentiment + rising social volume = сильный buy-сигнал.
- **Sentiment divergence**: цена растёт, но sentiment падает → ослабление тренда.
- **Sentiment spike как catalyst detector**: резкий рост social volume за 1-4 часа предшествует крупному движению (direction agnostic).

### Решающее правило

```
IF trend_indicators == BULLISH AND sentiment == EXTREME_FEAR:
    // Contrarian: все боятся, но тренд бычий → BUY с увеличенной позицией
    action = BUY, confidence = HIGH

IF trend_indicators == BEARISH AND sentiment == EXTREME_FEAR:
    // Follower: тренд + сентимент совпадают → SHORT, но осторожно (дно близко)
    action = SHORT, confidence = MEDIUM

IF trend_indicators == BULLISH AND sentiment == EXTREME_GREED:
    // Follower: всё совпадает → BUY, но уменьшить позицию (перекупленность)
    action = BUY, confidence = MEDIUM, position_scale = 0.5

IF trend_indicators == BEARISH AND sentiment == EXTREME_GREED:
    // Contrarian + Follower: тренд разворачивается, все ещё в эйфории → SHORT
    action = SHORT, confidence = HIGH
```

**Вывод**: sentiment работает И как contrarian, И как follower. Решающий фактор — **совпадает ли он с ценовыми индикаторами**. При совпадении → follower (подтверждение). При расхождении → contrarian (разворотный).

---

## Noise Filtering: Bot Detection и очистка сигнала

### Проблема

40-60% крипто-социального трафика — боты. Без фильтрации sentiment = noise.

### Многоуровневый фильтр

#### Уровень 1: Account-level фильтры (Twitter/Reddit)

```rust
pub struct BotDetector {
    min_account_age_days: u32,     // 30
    min_followers: u32,             // 50
    max_post_frequency: f64,        // постов/час ( > 10 = bot)
}

impl BotDetector {
    pub fn is_bot(&self, account: &AccountMetrics) -> bool {
        account.age_days < self.min_account_age_days
            || account.followers < self.min_followers
            || account.posts_per_hour > self.max_post_frequency
            || account.follower_following_ratio < 0.1  // 1000 following, 50 followers = bot
            || account.default_profile_image    // стандартная аватарка
    }
}
```

#### Уровень 2: Content-level фильтры

```rust
pub struct ContentFilter {
    // Дубликаты
    seen_hashes: HashSet<u64>,
    
    // Спам-паттерны
    spam_patterns: Vec<Regex>,  // "join our group", "100x guaranteed", URL shorteners
    
    // Минимальное качество
    min_text_length: usize,     // 20 символов
    max_emoji_ratio: f64,       // > 50% эмодзи = noise
    max_url_ratio: f64,         // > 30% ссылок = промо
}

impl ContentFilter {
    pub fn is_quality(&self, text: &str) -> bool {
        if text.len() < self.min_text_length { return false; }
        
        let emoji_count = text.chars().filter(|c| is_emoji(*c)).count();
        if emoji_count as f64 / text.len() as f64 > self.max_emoji_ratio { return false; }
        
        for pattern in &self.spam_patterns {
            if pattern.is_match(text) { return false; }
        }
        
        let hash = simhash(text);
        if self.seen_hashes.contains(&hash) { return false; }
        
        true
    }
}
```

#### Уровень 3: Statistical outlier removal

```rust
pub fn remove_outliers(scores: &[f64]) -> Vec<f64> {
    let mean = scores.iter().sum::<f64>() / scores.len() as f64;
    let std = (scores.iter().map(|x| (x - mean).powi(2)).sum::<f64>() / scores.len() as f64).sqrt();
    
    scores.iter()
        .filter(|&&x| (x - mean).abs() <= 2.0 * std)  // убираем > 2σ
        .copied()
        .collect()
}
```

#### Уровень 4: Cross-source validation

```rust
/// Sentiment валиден только если 2+ источника согласны
pub fn validate_across_sources(signals: &[SourceSignal]) -> Option<f64> {
    let positive_sources = signals.iter().filter(|s| s.sentiment > 0.2).count();
    let negative_sources = signals.iter().filter(|s| s.sentiment < -0.2).count();
    
    if positive_sources >= 2 {
        Some(signals.iter().map(|s| s.sentiment).sum::<f64>() / signals.len() as f64)
    } else if negative_sources >= 2 {
        Some(signals.iter().map(|s| s.sentiment).sum::<f64>() / signals.len() as f64)
    } else {
        None  // нет консенсуса → игнорировать
    }
}
```

#### Уровень 5: Time-based smoothing

```rust
pub struct SentimentAggregator {
    ema_fast: Ema,   // период 4 (1 час при 15мин обновлении)
    ema_slow: Ema,   // период 12 (3 часа)
    z_score_window: VecDeque<f64>,
}

impl SentimentAggregator {
    pub fn update(&mut self, raw: f64) -> AggregatedSentiment {
        let fast = self.ema_fast.update(raw);
        let slow = self.ema_slow.update(raw);
        
        // Z-score для определения аномалий
        self.z_score_window.push_back(raw);
        if self.z_score_window.len() > 48 { self.z_score_window.pop_front(); }
        
        let mean = self.z_score_window.iter().sum::<f64>() / self.z_score_window.len() as f64;
        let std = (self.z_score_window.iter().map(|x| (x - mean).powi(2)).sum::<f64>()
            / self.z_score_window.len() as f64).sqrt();
        let z_score = if std > 0.001 { (raw - mean) / std } else { 0.0 };
        
        AggregatedSentiment {
            raw,
            fast_ema: fast,
            slow_ema: slow,
            z_score,
            is_anomaly: z_score.abs() > 2.0,
        }
    }
}
```

---

## Агрегированная сентимент-метрика

### Композитный индекс

```rust
#[derive(Debug, Clone)]
pub struct CompositeSentiment {
    pub score: f64,              // -1..1
    pub confidence: f64,         // 0..1 (сколько источников согласны)
    pub contrarian_signal: f64,  // -1..1 (extreme = сильный)
    pub follower_signal: f64,    // -1..1 (alignment with trend)
    pub components: Vec<SourceComponent>,
}

#[derive(Debug, Clone)]
pub struct SourceComponent {
    pub name: String,
    pub weight: f64,
    pub value: f64,
    pub freshness: f64,   // 0..1, насколько свежие данные
}

pub fn compute_composite(
    fng: Option<&FearGreedSignal>,
    twitter: Option<&TwitterSentiment>,
    reddit: Option<&RedditSentiment>,
    news: Option<&NewsSentimentSignal>,
    funding: Option<&FundingSentiment>,
    lsr: Option<&LsrSignal>,
    google: Option<&GoogleTrendsSignal>,
) -> CompositeSentiment {
    
    let mut components = Vec::new();
    
    // Веса источников (сумма = 1.0)
    if let Some(f) = fng {
        components.push(SourceComponent { name: "fng".into(), weight: 0.15, value: f.normalized, freshness: 1.0 });
    }
    if let Some(t) = twitter {
        components.push(SourceComponent { name: "twitter".into(), weight: 0.15, value: t.smoothed, freshness: 1.0 });
    }
    if let Some(r) = reddit {
        components.push(SourceComponent { name: "reddit".into(), weight: 0.10, value: r.combined, freshness: 1.0 });
    }
    if let Some(n) = news {
        components.push(SourceComponent { name: "news".into(), weight: 0.15, value: n.score, freshness: 1.0 });
    }
    if let Some(f) = funding {
        components.push(SourceComponent { name: "funding".into(), weight: 0.25, value: f.sentiment, freshness: 1.0 });
    }
    if let Some(l) = lsr {
        components.push(SourceComponent { name: "lsr".into(), weight: 0.10, value: l.sentiment, freshness: 1.0 });
    }
    if let Some(g) = google {
        components.push(SourceComponent { name: "google".into(), weight: 0.10, value: g.sentiment, freshness: 1.0 });
    }
    
    // Нормализация весов (только активные источники)
    let total_weight: f64 = components.iter().map(|c| c.weight).sum();
    
    let composite_score = components.iter()
        .map(|c| c.value * c.weight / total_weight)
        .sum::<f64>();
    
    // Confidence: доля источников, которые дают сигнал того же знака
    let positive = components.iter().filter(|c| c.value > 0.1).count();
    let negative = components.iter().filter(|c| c.value < -0.1).count();
    let agreement = positive.max(negative) as f64 / components.len() as f64;
    
    CompositeSentiment {
        score: composite_score,
        confidence: agreement,
        contrarian_signal: composite_score.abs(),  // extreme = сильный contrarian
        follower_signal: composite_score,           // направление = follower
        components,
    }
}
```

---

## Интеграция с торговым движком

```rust
/// Как бот использует сентимент
pub fn sentiment_adjustment(composite: &CompositeSentiment, trend: TrendDirection) -> TradeAdjustment {
    let sentiment = composite.score;
    let confidence = composite.confidence;
    
    // Согласованность sentiment с трендом
    let aligned = match trend {
        TrendDirection::Bullish => sentiment > 0.0,
        TrendDirection::Bearish => sentiment < 0.0,
        TrendDirection::Neutral => true,
    };
    
    let position_scale = if aligned && confidence > 0.6 {
        // Sentiment подтверждает тренд → увеличиваем позицию
        1.0 + 0.2 * sentiment.abs()  // +20% максимум
    } else if !aligned && sentiment.abs() > 0.5 {
        // Sentiment против тренда → contrarian или уменьшаем
        if sentiment.abs() > 0.7 {
            // Extreme: contrarian reversal signal
            0.5  // сократить позицию, ждать подтверждения
        } else {
            0.75 // уменьшить
        }
    } else {
        1.0  // нейтрально
    };
    
    TradeAdjustment {
        position_scale: position_scale.clamp(0.25, 1.5),
        contrarian_alert: sentiment.abs() > 0.7 && confidence > 0.6,
        volatility_warning: composite.components.iter()
            .any(|c| c.name == "social_volume" && c.value > 2.0),  // spike
    }
}

pub struct TradeAdjustment {
    pub position_scale: f64,
    pub contrarian_alert: bool,
    pub volatility_warning: bool,
}
```

---

## Выбранные 1–3 лучших источника

### 🥇 1. Funding Rate

**Почему #1**:
- Отражает **реальные деньги** (не слова). Трейдеры ставят капитал → это сильнее любого твита.
- Contrarian accuracy ~65-70% на экстремальных значениях.
- Бесплатные API (биржевые), обновление каждые 8 часов.
- Простая реализация (~100 строк Rust).
- Уже интегрирован с деривативной торговлей бота.

**Отклонено против**: все social-источники проигрывают по noise-to-signal ratio.

### 🥈 2. Crypto Fear & Greed Index

**Почему #2**:
- Агрегирует 6 компонентов в одну метрику → готовый композитный индикатор.
- Extreme values (< 20, > 80) — надёжные contrarian сигналы.
- Бесплатный API, минимум кода.
- Дневной контекст: дополняет внутридневные индикаторы.

**Ограничение**: обновляется раз в день → слишком медленно для 1H стратегии. Используется как daily filter.

### 🥉 3. News Sentiment (NLP)

**Почему #3**:
- Даёт **контекст**: почему движется цена (SEC, hack, ETF, regulation).
- Breaking news = catalyst detector.
- CryptoPanic API бесплатен, RSS — тоже.
- NLP модель может быть лёгкой (VADER для MVP, transformer для v0.3+).

**Отклонено против Twitter**: Twitter более шумный, требует платный API, сложнее фильтрация ботов.

---

## Конфигурация

```yaml
# === Sentiment ===
sentiment:
  # Включить модуль сентимента
  enabled: true
  
  # Источники
  sources:
    funding:
      enabled: true
      weight: 0.40
      exchanges: ["binance", "bybit"]
      extreme_threshold: 0.0005  # 0.05%
    
    fear_greed:
      enabled: true
      weight: 0.30
      extreme_fear: 20
      extreme_greed: 80
      cache_hours: 24
    
    news:
      enabled: true
      weight: 0.30
      sources: ["cryptopanic", "coindesk", "cointelegraph"]
      nlp_model: "vader"          # v0.1: vader, v0.3: transformer
      freshness_decay_hours: 24
      min_confidence: 0.5
  
  # Noise filtering
  filter:
    bot_detection: true
    min_account_age_days: 30
    min_text_length: 20
    outlier_std_threshold: 2.0
    cross_source_min_agreement: 2  # минимум 2 источника должны согласиться
  
  # Contrarian thresholds
  contrarian:
    enable: true
    extreme_threshold: 0.7        # |sentiment| > 0.7 = extreme
    min_confidence: 0.6           # agreement > 60%
    position_scale_min: 0.25
    position_scale_max: 1.5
```

---

## Roadmap

| Версия | Что добавить |
|---|---|
| **v0.1** | Funding Rate + F&G + News (VADER) — базовая тройка |
| **v0.2** | Twitter Sentiment (transformer), Bot detection, Z-score anomaly |
| **v0.3** | Google Trends, Social Volume (LunarCrush), Cross-source validation |
| **v0.5** | Telegram, Reddit deep analysis, Custom fine-tuned NLP model |

---

## Антипаттерны сентимент-анализа

| # | Что запрещено | Почему |
|---|---|---|
| 1 | Использовать sentiment как primary signal | Sentiment — фильтр, не триггер |
| 2 | Contrarian trade без подтверждения трендом | Extreme fear в downtrend = catching falling knife |
| 3 | Не фильтровать ботов | 40-60% noise → мусорный сигнал |
| 4 | Использовать один источник | Один источник = один point of failure |
| 5 | Не кэшировать API ответы | Rate limit + latency |
| 6 | Обновлять F&G чаще раза в день | API обновляется раз в день |
| 7 | Ignoring funding rate | Лучший сентимент-индикатор для деривативов |
| 8 | Raw sentiment без сглаживания | Высокочастотный шум |

---

## Итого

Sentiment analysis для крипто-бота — это не про «читать твиты», а про измерять **позиционирование участников рынка** (funding, L/S ratio) и **уровень эмоций** (F&G, news). Лучший сентимент = тот, который отражает реальные деньги (funding rate), а не слова. Contrarian логика работает на экстремумах, но только с подтверждением ценовых индикаторов. Noise filtering — критически важен, без него sentiment = random number generator.