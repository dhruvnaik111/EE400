import requests
import time
import random

# Network & Hardware Configuration 
MACHINE1_IP = "169.254.157.246"  # Alice and Bob
MACHINE2_IP = "169.254.15.141"   # Eve
PORT = 8080

# Minimum photon count on Channel 2 to register as a "detection"
DETECTION_THRESHOLD = 50 

def send_qued_command(ip, action, param, value=None):
    """Sends the HTTP GET request to the quED API."""
    url = f"http://{ip}:{PORT}/?action={action}&param={param}"
    if value is not None:
        url += f"&value={value}"
    try:
        response = requests.get(url, timeout=5)
        return response.text.strip()
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with {ip}: {e}")
        return None

def run_physical_bb84_with_eve(alice_file, bob_file, test_limit=50):
    # Read the random number files
    with open(alice_file, 'r') as f:
        alice_data = f.read().strip()
    with open(bob_file, 'r') as f:
        bob_data = f.read().strip()
        
    min_len = min(len(alice_data), len(bob_data))
    reconciled_key = []
    
    # Motor Angle Mappings based on (Basis, Bit)
    # Basis 0 = H/V, Basis 1 = Diagonal (+/-)
    alice_hwp_angles = {
        ('0', '0'): 0.0,    # H -> 0 deg
        ('0', '1'): 45.0,   # V -> 90 deg (HWP at 45)
        ('1', '0'): 22.5,   # + -> +45 deg (HWP at 22.5)
        ('1', '1'): -22.5   # - -> -45 deg (HWP at -22.5)
    }
    
    bob_pol_angles = {
        ('0', '0'): 0.0,    # Measure H
        ('0', '1'): 90.0,   # Measure V
        ('1', '0'): 45.0,   # Measure +
        ('1', '1'): -45.0   # Measure -
    }

    # Eve's possible measurement angles mapping to H, V, + and -
    eve_possible_angles = [0.0, 90.0, 45.0, -45.0]

    print("Starting Physical BB84 Protocol with Eve...")
    print(f"Testing first {test_limit} iterations.\n")

    iteration = 0
    for i in range(0, min_len - 1, 2):
        if iteration >= test_limit:
            break
            
        alice_basis, alice_bit = alice_data[i], alice_data[i+1]
        bob_basis, bob_bit = bob_data[i], bob_data[i+1]
        
        # 1. Lookup the physical angles for Alice and Bob
        alice_angle = alice_hwp_angles[(alice_basis, alice_bit)]
        bob_angle = bob_pol_angles[(bob_basis, bob_bit)]
        
        # 2. Eve randomly selects her measurement angle
        eve_angle = random.choice(eve_possible_angles)
        
        # 3. Command the motors to move
        # Machine 1: Set Alice and Bob
        send_qued_command(MACHINE1_IP, "set", "pm1", alice_angle)
        send_qued_command(MACHINE1_IP, "set", "pm2", bob_angle)
        
        # Machine 2: Set Eve (Assuming plugged into pm1)
        send_qued_command(MACHINE2_IP, "set", "pm1", eve_angle)
        
        # 4. Wait for physical rotation to complete 
        time.sleep(0.5)
        
        # 5. Fetch the photon counts from Bob's detector on Machine 1
        counts_response = send_qued_command(MACHINE1_IP, "get", "cnt")
        
        # UPDATED MULTILINE PARSING LOGIC FOR APD 2 
        single_2_count = 0
        if counts_response:
            for line in counts_response.split('\n'):
                line = line.strip()
                # Look specifically for the line that starts with "2:"
                if line.startswith('2:'):
                    try:
                        # Split by the colon and grab the number on the right
                        single_2_count = int(line.split(':')[1].strip())
                    except ValueError:
                        print(f"Warning: Could not parse integer from line -> {line}")
                    break # Stop searching once we find detector 2
        else:
            print("Warning: Received empty count response from quED.")

        # 6. Determine if we keep the bit based on Bob's detection
        photon_detected = single_2_count > DETECTION_THRESHOLD
        bases_match = (alice_basis == bob_basis)
        
        status = "Discarded"
        if bases_match and photon_detected:
            reconciled_key.append(alice_bit)
            status = "KEPT"
            
        print(f"Iter {iteration+1} | Alice: {alice_angle}° Bob: {bob_angle}° Eve: {eve_angle}° | Count: {single_2_count} | {status}")
        
        iteration += 1

    print("\n Hardware Run Complete")
    print(f"Secure Key Generated: {''.join(reconciled_key)}")
    print(f"Key Length: {len(reconciled_key)} bits")

if __name__ == "__main__":
    run_physical_bb84_with_eve("ZufallAliceMain.txt", "ZufallBobMain.txt", test_limit=100)