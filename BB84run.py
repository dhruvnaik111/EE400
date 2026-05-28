def generate_bb84_key(alice_file, bob_file):
    # Read the text files
    with open(alice_file, 'r') as f:
        alice_data = f.read().strip()
    with open(bob_file, 'r') as f:
        bob_data = f.read().strip()
        
    # Ensure both files are the same length
    min_len = min(len(alice_data), len(bob_data))
    
    reconciled_key = []
    total_photons_sent = 0
    sifted_mismatched_basis = 0
    sifted_no_detection = 0

    # Process bits in chunks of 2 (Basis, Bit)
    for i in range(0, min_len - 1, 2):
        total_photons_sent += 1
        
        alice_basis = alice_data[i]
        alice_bit = alice_data[i+1]
        
        bob_basis = bob_data[i]
        bob_bit = bob_data[i+1]
        
        # 1. Did Bob physically detect a photon?
        # In a single polarizer setup, Bob only gets a deterministic click 
        # if the bases match AND the bits match. 
        # (If bases mismatch, he gets a click 50% of the time, but those get thrown out anyway).
        if alice_basis == bob_basis:
            if alice_bit == bob_bit:
                # Photon detected and bases match! Key bit generated.
                reconciled_key.append(alice_bit)
            else:
                # Photon blocked by polarizer. No detection.
                sifted_no_detection += 1
        else:
            # Bases mismatched. Discarded during public communication.
            sifted_mismatched_basis += 1

    final_key_string = "".join(reconciled_key)
    
    print(f"--- BB84 Protocol Results ---")
    print(f"Total Photons Sent: {total_photons_sent}")
    print(f"Discarded (Basis Mismatch): {sifted_mismatched_basis}")
    print(f"Discarded (No Detection): {sifted_no_detection}")
    print(f"Final Secure Key Length: {len(reconciled_key)} bits")
    
    # Check if we have enough bits for the 32x32 image (1024 bits)
    if len(reconciled_key) >= 1024:
        print("\nSuccess! You have enough bits to encode the 32x32 image.")
        print(f"Your Key (First 256 bits): {final_key_string[:256]}...")
    else:
        print(f"\nWarning: You only generated {len(reconciled_key)} bits.")
        print("You need 1024 bits for a 32x32 image. You may need longer RNG strings.")

    return final_key_string

# To run this, place ZufallAliceMain.txt and ZufallBobMain.txt in the same directory
# generated_key = generate_bb84_key("ZufallAliceMain.txt", "ZufallBobMain.txt")