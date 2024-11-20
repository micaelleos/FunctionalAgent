# Functional AI Agent for Jira Integration

## Overview
This project is a **Functional AI Agent** designed to assist users in building **functional documentations** and seamlessly integrate with **Jira**. Using cutting-edge AI, this agent helps users generate and refine **User Stories** and other functional requirements. Once the User Stories are ready, they can be automatically exported to the desired Jira project.

The application leverages **Python**, **Streamlit** for the user interface, and **LangChain** for managing the AI interactions, ensuring a robust and intuitive experience.

---

## Key Features
- **AI-Powered Documentation**: Generate and refine functional documentations and User Stories based on user input.
- **Jira Integration**: Directly export finalized User Stories to your Jira project, streamlining the development workflow.
- **Intuitive Interface**: Built with Streamlit for a clean and easy-to-use UI.
- **Context-Aware Suggestions**: Provides actionable recommendations for improving your documentation quality.

---

## Tech Stack
- **Python**: Core programming language for the application.
- **Streamlit**: Simplified framework for building interactive web applications.
- **LangChain**: Framework to build and manage AI-powered functionalities.
- **Jira API**: To interact with Jira for creating issues directly from the application.

---

## Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/micaelleos/FunctionalAgent.git
   cd FunctionalAgent
   ```

2. **Set Up a Virtual Environment**
   ```bash
   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Environment Variables**
   - Create a `.env` file in the root directory with the following:
     ```env
     OPENAI_API_KEY=your-openai-api-key
     ```
   Replace the placeholders with your actual credentials.

5. **Run the Application**
   ```bash
   streamlit run app.py
   ```

---

## Usage

1. **Generate Functional Documentation**
   - Start the application and input a description of your project or requirements.
   - The agent will generate User Stories and suggest improvements.

2. **Refine the Stories**
   - Review and edit the generated stories as needed.

3. **Export to Jira**
   - Select the stories you wish to export and specify the Jira project key.
   - Click **Export**, and the agent will create the issues in Jira.

---

## Example Workflow

1. Enter your jira credentials. Click in gear icon.
2. Describe the feature: _"As a user, I want to log in using my email and password."_
3. The agent generates:
   ```
   User Story:
   - As a user, I want to log in using my email and password so that I can access my account securely.
   Acceptance Criteria:
   - The system validates user credentials.
   - Invalid attempts show an appropriate error message.
   ```
4. Refine the story and add additional details if necessary.
5. Ask the agent to export it to Jira under the project key you want (**PROJ**).

---

## Contributing

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/new-feature`.
3. Commit your changes: `git commit -m 'Add a new feature'`.
4. Push to the branch: `git push origin feature/new-feature`.
5. Open a Pull Request.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Contact

For any questions, feel free to reach out:
- **Email**: micaelle.osouza@gmail.com
---

Happy Building 🚀