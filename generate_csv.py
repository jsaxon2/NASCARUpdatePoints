import os
import google.generativeai as genai

# Configure Gemini API
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

def generate_weekly_csv():
    # Prompting Gemini for structured CSV output
    prompt = """
    Provide the NASCAR Cup Series race results for the most recent completed race.
    Format the output strictly as a CSV block without markdown code fences or extra explanations.
    
    Header format:
    Position,First_Name,Last_Name,Points,Stage_1,Stage_2,Stage_3,Fastest_Lap
    """

    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)

    # Clean response and write to file
    csv_text = response.text.strip().replace("```csv", "").replace("```", "")
    
    with open("race_results.csv", "w", encoding="utf-8") as f:
        f.write(csv_text)
        
    print("race_results.csv created successfully!")

if __name__ == "__main__":
    generate_weekly_csv()
