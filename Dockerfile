# Use the base image
FROM pathwaycom/pathway:latest

# Set the working directory
WORKDIR /app

# Update the package list and install required packages
RUN apt-get update \
    && apt-get install -y python3-opencv tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install -U --no-cache-dir -r requirements.txt

# Expose port 8080 for GCP
EXPOSE 8080

# Copy the rest of the application files
COPY . .

# Command to run the application
CMD ["python", "app.py"]
