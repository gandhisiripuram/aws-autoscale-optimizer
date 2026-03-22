import network.CreateNetwork
import compute.CreateCompute
import automation.CreateLambdaEvent

def main():
    print("Step 1: Starting Network Layer Initialization...")
    network.CreateNetwork.main()
    
    print("\nStep 2: Starting Compute Layer Initialization...")
    compute.CreateCompute.main()

    print("\nStep 3: Starting Automation Layer (Lambda/EventBridge)...")
    automation.CreateLambdaEvent.main()

if __name__ == "__main__":
    main()