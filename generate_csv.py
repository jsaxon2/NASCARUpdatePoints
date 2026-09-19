import os
from google import genai

# Initialize the Gemini Client using your repository secret
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

def generate_weekly_csv():
    prompt = """
    Provide the NASCAR Cup Series race results for the most recent completed race.
    Format the output strictly as a CSV block without markdown code fences or extra text.
    
    Header format:
    Position,First_Name,Last_Name,Points,Stage_1,Stage_2,Stage_3,Fastest_Lap
    """

    # Call Gemini using the modern Google Gen AI SDK
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )

    # Clean output
    csv_text = response.text.strip().replace("```csv", "").replace("```", "")
    
    with open("race_results.csv", "w", encoding="utf-8") as f:
        f.write(csv_text)
        
    print("race_results.csv created successfully!")

if __name__ == "__main__":
    generate_weekly_csv()
