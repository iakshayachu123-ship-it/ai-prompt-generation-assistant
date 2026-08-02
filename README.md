# AI Prompt Generation Assistant

An AI-powered Django web application that generates high-quality prompts for image generation, thumbnail creation, and AI-assisted image editing workflows.

---

## Features

### 🖼️ Image Prompt Generator
Upload an image and describe your idea. The application analyzes the image and generates a detailed prompt optimized for AI image generation models.

### 🎨 Thumbnail Prompt Generator
Upload an image and specify the desired theme or style. The application creates professional thumbnail prompts for use with AI image generation tools.

### ✨ Image Editing Prompt Generator
Upload your image along with a reference image. The application analyzes both images and generates a detailed editing prompt that captures the reference image's lighting, color grading, composition, mood, and visual style.

---

## Tech Stack

- Python
- Django
- HTML
- CSS
- JavaScript
- Bootstrap
- Groq API
- Git

---

## Screenshots

> Add screenshots of the following pages.

- Home Page
- Image Prompt Generator
- Thumbnail Prompt Generator
- Image Editing Prompt Generator

---

## Installation

### Clone the repository

```bash
git clone https://github.com/yourusername/ai-prompt-generation-assistant.git
cd ai-prompt-generation-assistant
```

### Create a virtual environment

```bash
python -m venv venv
```

### Activate the virtual environment

Windows

```bash
venv\Scripts\activate
```

Linux / macOS

```bash
source venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Configure Environment Variables

Create a `.env` file in the project root.

Example:

```env
GROQ_API_KEY=your_groq_api_key
```

### Run migrations

```bash
python manage.py migrate
```

### Start the development server

```bash
python manage.py runserver
```

Open:

```
http://127.0.0.1:8000/
```

---

## Project Structure

```
photo_prompt_app/
│
├── photo_prompt_project/
├── prompt_generator/
├── templates/
├── static/
├── manage.py
├── requirements.txt
└── README.md
```

---

## Future Improvements

- User Authentication
- Prompt History
- Export Prompts
- Multiple AI Model Support
- Dark Mode
- Prompt Templates

---

## Author

**Akshay N**

GitHub: https://github.com/iakshayachu123-ship-it

LinkedIn: *(Add your LinkedIn URL here)*

---

## License

This project is intended for learning and portfolio purposes.
