import os
import time
import json
import openai

# Step 1: Set up environment variables and install the OpenAI library.
# Make sure to run: pip install --upgrade openai
openai.api_key = os.getenv("OPENAI_API_KEY")

# Step 2: Read your JSON file containing context.
# For example, suppose you have a file named "context.json"
with open("context.json", "r") as f:
    context_data = json.load(f)

# Prepare your prompt – you can incorporate the context from your file.
# For example, you might want to prepend the context to your prompt.
prompt = f"Context: {json.dumps(context_data)}\n\nTask: Provide a detailed analysis on the above context."

# Step 3: Create a JSON Lines (.jsonl) file for batch requests.
# Each line represents one request. You may want to create one request per line.
# For demonstration, we create one request with a custom_id.
request_body = {
    "custom_id": "task-001",
    "method": "POST",
    "url": "/chat/completions",
    "body": {
        "model": "o3-mini",
        "messages": [
            {"role": "developer", "content": "Formatting re-enabled - please enclose code blocks with markdown tags."},
            {"role": "user", "content": prompt}
        ],
        # Optionally, include additional model parameters (e.g., reasoning effort)
        "reasoning_effort": "medium",
        "max_tokens": 1000
    }
}

# Write this request to a JSONL file.
jsonl_filename = "batch_requests.jsonl"
with open(jsonl_filename, "w") as outfile:
    outfile.write(json.dumps(request_body) + "\n")
    
print(f"Created batch request file: {jsonl_filename}")

# Step 4: Upload the JSONL file to OpenAI for batch processing.
# The file upload is done with purpose "batch".
upload_response = openai.File.create(
    file=open(jsonl_filename, "rb"),
    purpose="batch"
)
input_file_id = upload_response.id
print(f"Uploaded file id: {input_file_id}")

# Step 5: Create a batch job that uses the uploaded file.
# Note: Adjust endpoint and parameters as needed. Here we target chat completions.
batch_response = openai.Batch.create(
    input_file_id=input_file_id,
    endpoint="/chat/completions",
    completion_window="24h"
)
batch_id = batch_response.id
print(f"Created batch job with id: {batch_id}")

# Step 6: Poll the batch job status until completed.
status = batch_response.status
while status not in ("completed", "failed", "cancelled"):
    print(f"Batch {batch_id} status: {status}. Waiting for 60 seconds...")
    time.sleep(60)
    batch_response = openai.Batch.retrieve(batch_id)
    status = batch_response.status

print(f"Batch job completed with status: {status}")

# Step 7: Retrieve and process the output file.
# The completed batch job returns an output_file_id.
output_file_id = batch_response.output_file_id
if output_file_id:
    output_file_response = openai.File.download(output_file_id)
    # The output file is expected to be in JSON Lines format.
    responses = output_file_response.decode("utf-8").strip().split("\n")
    for line in responses:
        response_data = json.loads(line)
        # Extract the assistant's response content
        content = response_data.get("response", {}).get("body", {}).get("choices", [{}])[0].get("message", {}).get("content", "")
        print(f"Response for {response_data.get('custom_id')}:")
        print(content)
else:
    print("No output file was generated.")

