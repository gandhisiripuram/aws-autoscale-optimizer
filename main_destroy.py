import automation.TearDownLambdaEvent
import compute.TearDownCompute
import network.TearDownNetwork

def main():
    print("Step 1: Initiating Automation Layer Teardown...")
    # Must delete EventBridge triggers before the ASG or Lambda
    automation.TearDownLambdaEvent.main()
    
    print("\nStep 2: Initiating Compute Layer Teardown...")
    compute.TearDownCompute.main()
    
    print("\nStep 3: Initiating Network Layer Teardown...")
    network.TearDownNetwork.main()

if __name__ == "__main__":
    main()