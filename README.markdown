# ServiceNow AI Agent

Welcome to the ServiceNow AI Agent project! This is a small automation tool I built to streamline IT ticket creation by monitoring emails and integrating with ServiceNow. It’s a work-in-progress, but it’s already doing some cool stuff—like creating tickets and sending approval emails automatically. I’m running this on my Mac, and I’d love for you to try it out or contribute if you’re interested!

## 📋 Project Overview

The ServiceNow AI Agent monitors a Gmail inbox (`projectdummy144@gmail.com`) for unread emails every 30 minutes, analyzes their content using the Google Gemini API, and creates tickets in a ServiceNow Personal Developer Instance (PDI). For change requests, it sends an approval email to a manager’s inbox (`dummymanager144@gmail.com`). Everything is scheduled via a cron job, and I’ve made sure to keep sensitive info secure in a `.env` file.

### Key Features
- Fetches unread emails using Gmail API.
- Analyzes email content with Google Gemini API (or a simple rule for "Change:" emails).
- Creates incidents or change requests in ServiceNow PDI.
- Sends approval emails for change requests.
- Logs all actions for debugging.

## 🛠️ Prerequisites

Before you get started, make sure you have the following:
- **Python 3.9+**: The script is written in Python.
- **PyCharm** (optional): I use PyCharm, but any IDE works.
- **macOS/Linux**: I’ve set this up on my Mac; it should work on Linux too, but I haven’t tested it on Windows yet.
- **ServiceNow PDI**: You’ll need a Personal Developer Instance (I’m using `https://dev305029.service-now.com`).
- **Google Cloud Project**: For Gmail and Gemini API access.
- **Cron**: To schedule the script (macOS/Linux has this built-in).

## 📦 Setup Instructions

Here’s how to get the project up and running:

1. **Clone the Repository**  
   ```bash
   git clone https://github.com/your-username/servicenow-ai-agent.git
   cd servicenow-ai-agent
   ```

2. **Set Up a Virtual Environment**  
   I recommend using a virtual environment to keep dependencies tidy.
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Dependencies**  
   Install the required Python packages.
   ```bash
   pip install requests google-api-python-client google-auth-oauthlib google-generativeai python-dotenv
   ```

4. **Configure Google APIs**  
   - **Gmail API**:
     1. Go to [Google Cloud Console](https://console.cloud.google.com/).
     2. Create a project, enable the Gmail API, and download the `credentials.json` file.
     3. Place `credentials.json` in the project root (`/path/to/servicenow-ai-agent/`).
   - **Gemini API**:
     1. Go to [Google AI Studio](https://aistudio.google.com/) and get an API key for `gemini-1.5-flash`.
     2. You’ll add this key to the `.env` file in the next step.

5. **Set Up the `.env` File**  
   Create a `.env` file in the project root with the following details:
   ```
   SNOW_URL=https://dev305029.service-now.com/api/now/table
   SNOW_USER=your_servicenow_username
   SNOW_PASS=your_servicenow_password
   GMAIL_ADDRESS=your_gmail_address
   MANAGER_EMAIL=your_manager_email
   GEMINI_API_KEY=your_gemini_api_key
   ```
   Secure the file:
   ```bash
   chmod 600 .env
   ```

6. **Schedule the Script with Cron**  
   I’ve set this up to run every 30 minutes. Edit your cron jobs:
   ```bash
   crontab -e
   ```
   Add this line (adjust the path to your project):
   ```
   */30 * * * * /path/to/servicenow-ai-agent/.venv/bin/python /path/to/servicenow-ai-agent/ServiceNowAgent.py >> /path/to/servicenow-ai-agent/cron_log.txt 2>&1
   ```

## 🚀 Usage

1. **Run Manually (For Testing)**  
   After setting up, you can run the script directly:
   ```bash
   python ServiceNowAgent.py
   ```
   The first time, it’ll prompt you to authenticate with Gmail via OAuth. Follow the link, sign in, and allow access. This creates a `token.pickle` file for future runs.

2. **Send a Test Email**  
   - Send an email to your `GMAIL_ADDRESS` (e.g., `projectdummy144@gmail.com`).
   - **Incident Example**: Subject: "Laptop Crashed", Body: "My laptop isn’t working!"
   - **Change Request Example**: Subject: "Software Install", Body: "Change: Install new software on server."
   - Wait for the next cron run (or run manually) to process the email.

3. **Check Outputs**  
   - **ServiceNow PDI**: Log into your PDI and look for new tickets (`INC...` or `CHG...`).
   - **Manager Email**: Check `MANAGER_EMAIL` for approval emails (subject: "Approval Needed for Ticket CHG...").
   - **Logs**: Open `ticket_log.txt` to see what happened.

## 📜 Logs

The script logs all actions to `ticket_log.txt` in the project directory. Here’s a sample:
```
2025-05-27 10:00:00: Starting ServiceNowAgent...
2025-05-27 10:00:01: Found 1 unread emails to process.
2025-05-27 10:00:02: Fetched email subject: Software Install
2025-05-27 10:00:03: Detected 'Change:' in email, assigning create_change action
2025-05-27 10:00:04: Ticket Created: CHG00000XX (ID: ...)
2025-05-27 10:00:05: Sent approval email for ticket CHG00000XX to dummymanager144@gmail.com
```

## ⚠️ Known Issues
- **Gemini API Quota**: The free tier has a 500 requests/day limit. If you hit this, the script will skip analysis for some emails (logs will show `Gemini quota exceeded`). Wait for the quota to reset at midnight Pacific Time (11:00 PM CDT), or get a new API key.
- **HTML Emails**: Some emails with only HTML content might be ignored. I’ve added basic HTML parsing, but it’s not perfect yet.
- **Duplicates**: The script tracks processed emails in `ticket_ids.txt`, but if you delete this file, it might reprocess emails.

## 🌟 Future Enhancements
- Add support for updating tickets (e.g., mark as "Resolved").
- Improve HTML email parsing for better content extraction.
- Build a simple UI to monitor the system in real-time.
- Add email notifications for errors (e.g., quota exhaustion).

## 🤝 Contributing
I’d love to hear your feedback or ideas! If you want to contribute:
1. Fork the repo.
2. Create a new branch (`git checkout -b feature/your-feature`).
3. Make your changes and commit (`git commit -m "Add your feature"`).
4. Push to your branch (`git push origin feature/your-feature`).
5. Open a pull request.

## 📬 Contact
Feel free to reach out if you have questions or need help setting this up:
- **Email**: saiganeshvuppala@example.com  
- **GitHub Issues**: Open an issue on this repo.

## 🙏 Acknowledgments
- Thanks to the ServiceNow community for their awesome PDI program.
- Shoutout to Google for providing free API access (even if the quota is a bit tricky!).

Happy automating! 🚀