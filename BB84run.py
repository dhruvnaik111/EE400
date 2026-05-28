import requests
import time
import random

# --- Network & Hardware Configuration ---
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

def run_physical_bb84_with_eve(alice_file, bob_file, test_limit=100):
    # Read the random number files
    with open(alice_file, 'r') as f:
        alice_data = f.read().strip()
    with open(bob_file, 'r') as f:
        bob_data = f.read().strip()
        
    min_len = min(len(alice_data), len(bob_data))
    
    alice_key = []
    bob_key = []
    bit_errors = 0
    
    # Motor Angle Mappings
    alice_hwp_angles = {
        ('0', '0'): 0.0,    # H
        ('0', '1'): 45.0,   # V
        ('1', '0'): 22.5,   # +
        ('1', '1'): -22.5   # -
    }
    
    bob_pol_angles = {
        ('0', '0'): 0.0,    # Measure H
        ('0', '1'): 90.0,   # Measure V
        ('1', '0'): 45.0,   # Measure +
        ('1', '1'): -45.0   # Measure -
    }

    eve_possible_angles = [0.0, 90.0, 45.0, -45.0]

    print("Starting Physical BB84 Protocol with Eve...")
    print(f"Executing {test_limit} iterations.\n")

    iteration = 0
    for i in range(0, min_len - 1, 2):
        if iteration >= test_limit:
            break
            
        alice_basis, alice_bit = alice_data[i], alice_data[i+1]
        bob_basis, bob_guess_bit = bob_data[i], bob_data[i+1]
        
        # 1. Lookup the physical angles
        alice_angle = alice_hwp_angles[(alice_basis, alice_bit)]
        bob_angle = bob_pol_angles[(bob_basis, bob_guess_bit)]
        eve_angle = random.choice(eve_possible_angles)
        
        # 2. Command the motors
        send_qued_command(MACHINE1_IP, "set", "pm1", alice_angle)
        send_qued_command(MACHINE1_IP, "set", "pm2", bob_angle)
        send_qued_command(MACHINE2_IP, "set", "pm1", eve_angle)
        
        # 3. Wait for physical rotation to complete 
        time.sleep(0.5)
        
        # 4. Fetch the photon counts
        counts_response = send_qued_command(MACHINE1_IP, "get", "cnt")
        
        # 5. Parse the HTML response for APD 2
        single_2_count = 0
        if counts_response:
            for line in counts_response.split('<br>'):
                line = line.strip()
                if line.startswith('2:'):
                    try:
                        single_2_count = int(line.split(':')[1].strip())
                    except ValueError:
                        pass
                    break

        # 6. Hardware Sifting Logic
        photon_detected = single_2_count > DETECTION_THRESHOLD
        bases_match = (alice_basis == bob_basis)
        
        status = "Discarded (Basis Mismatch or No Photon)"
        
        # We only care about iterations where the bases match
        if bases_match:
            if photon_detected:
                # If a photon is detected Bob registers the bit he was measuring for
                # Alice registers the bit she sent
                alice_key.append(alice_bit)
                bob_key.append(bob_guess_bit)
                
                # Check if this physical detection was an error
                if alice_bit != bob_guess_bit:
                    bit_errors += 1
                    status = "KEPT (ERROR DETECTED)"
                else:
                    status = "KEPT (Valid Bit)"
        
        print(f"Iter {iteration+1} | Alice: {alice_angle}° Bob: {bob_angle}° Eve: {eve_angle}° | Count: {single_2_count} | {status}")
        iteration += 1

    # --- Post-Experiment QBER Calculation ---
    alice_final_str = "".join(alice_key)
    bob_final_str = "".join(bob_key)
    
    qber = (bit_errors / len(alice_key)) * 100 if len(alice_key) > 0 else 0

    print("\n" + "="*40)
    print("--- Physical Hardware Run Complete ---")
    print("="*40)
    print(f"Final Key Length: {len(alice_key)} bits")
    print(f"Total Bit Errors: {bit_errors}")
    print(f"Physical QBER:    {qber:.2f}%")
    print("-" * 40)
    print(f"Alice's Key: {alice_final_str}")
    print(f"Bob's Key:   {bob_final_str}")
    print("="*40)

if __name__ == "__main__":
    # Change test_limit to the total number of iterations you want to run
    run_physical_bb84_with_eve("ZufallAliceMain.txt", "ZufallBobMain.txt", test_limit=100)