import sys
import time
import grpc
import threading
import concurrent.futures

# Make sure we can import the generated protos
sys.path.append('src/gateway')
import market_data_pb2
import market_data_pb2_grpc

class MarketDataGatewayServicer(market_data_pb2_grpc.MarketDataGatewayServicer):
    def StreamTicks(self, request_iterator, context):
        count = 0
        for tick in request_iterator:
            count += 1
            # Simulate minimal processing
            _ = tick.price * tick.volume
        return market_data_pb2.TickResponse(success=True, ticks_processed=count)

def serve():
    server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=2))
    market_data_pb2_grpc.add_MarketDataGatewayServicer_to_server(MarketDataGatewayServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    return server

def run_client():
    channel = grpc.insecure_channel('localhost:50051')
    stub = market_data_pb2_grpc.MarketDataGatewayStub(channel)
    
    def generate_ticks(n=10000):
        for i in range(n):
            yield market_data_pb2.Tick(
                symbol="BTCUSDT",
                price=50000.0 + i,
                volume=1.0,
                is_buyer_maker=True,
                timestamp=int(time.time() * 1000)
            )

    start_time = time.perf_counter()
    response = stub.StreamTicks(generate_ticks(10000))
    end_time = time.perf_counter()
    
    total_time = end_time - start_time
    avg_latency = (total_time / 10000) * 1_000_000 # in microseconds
    
    print(f"Processed {response.ticks_processed} ticks in {total_time:.4f} seconds.")
    print(f"Average Latency per tick: {avg_latency:.2f} microseconds")

if __name__ == '__main__':
    server = serve()
    time.sleep(1) # let server start
    run_client()
    server.stop(0)
