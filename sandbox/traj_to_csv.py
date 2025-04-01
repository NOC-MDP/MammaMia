import csv

def generate_csv(file_name, num_rows):
    # Open the CSV file for writing
    with open(file_name, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)

        # Write the header
        csvwriter.writerow(['Row', 'Location', 'Rotation'])

        # Initialize variables for the first row
        x = 0.0
        y = 0.0
        z = 0.0
        pitch = 0.0
        yaw = 0.0
        roll = 0.0

        # Generate rows following the pattern
        for i in range(1, num_rows + 1):
            row_id = f"AUV1-TS{i}"

            # Write the current row to the CSV
            location = f"(X={x:.3f}, Y={y:.3f}, Z={z:.3f})"
            rotation = f"(Pitch={pitch:.3f}, Yaw={yaw:.3f}, Roll={roll:.3f})"
            csvwriter.writerow([row_id, location, rotation])

            # Update x and z for the next row
            x -= 100.0
            z += 5000.0


# Generate a CSV with 10 rows
generate_csv('auv_data.csv', 10000)

print("CSV file 'auv_data.csv' has been generated.")
