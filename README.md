# 📸 PicSource

> A cloud-native image gallery web application built with Flask, MongoDB, and Tailwind CSS.

PicSource is a full-stack image-sharing platform that allows users to upload, browse, and manage photos through a modern, responsive interface. Developed as part of the **Cloud Native Development** module, the project demonstrates core cloud-native principles: separation of concerns between frontend and backend, externalised configuration, stateless request handling, and a NoSQL persistence layer suited for horizontal scaling.

---

## 🚀 Features

- **Image Upload** — Upload images with metadata (title, description, tags) through a clean, validated form.
- **Gallery View** — Browse uploaded images in a responsive grid layout powered by Tailwind CSS and DaisyUI.
- **Image Metadata Storage** — Each upload is persisted to MongoDB with associated metadata for retrieval and filtering.
- **Static File Serving** — Uploaded images are served via Flask's static file handling.
- **Environment-Based Configuration** — Sensitive values (DB URI, secret keys) are loaded via `.env` for portability across environments.
- **Modular Architecture** — Clear separation between backend logic, frontend templates, and static assets.

---

## 🛠️ Tech Stack

| Layer        | Technology                          |
| ------------ | ----------------------------------- |
| **Backend**  | Python, Flask, PyMongo              |
| **Database** | MongoDB                             |
| **Frontend** | HTML5, Jinja2 Templates             |
| **Styling**  | Tailwind CSS, DaisyUI               |
| **Config**   | python-dotenv                       |


---

## ⚙️ Getting Started

### Prerequisites

- Python 3.10+
- MongoDB (local instance or MongoDB Atlas)
- pip

### Installation

1. **Clone the repository**
```bash
   git clone https://github.com/farhanbin65/PicSource.git
   cd PicSource
```

2. **Create a virtual environment**
```bash
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
   pip install -r requirements.txt
```

4. **Configure environment variables**

   Create a `.env` file in the project root:
```env
   FLASK_APP=backend/app.py
   FLASK_ENV=development
   SECRET_KEY=your-secret-key-here
   MONGO_URI=mongodb://localhost:27017/picsource
   UPLOAD_FOLDER=uploads
```

5. **Run the application**
```bash
   flask run
```

   The app will be available at `http://localhost:5000`.

---

## ☁️ Cloud-Native Design Principles

This project was designed with the [Twelve-Factor App](https://12factor.net/) methodology in mind:

- **Config in the environment** — All credentials and environment-specific values are stored in `.env`, never hard-coded.
- **Stateless processes** — The Flask application does not hold session state in memory; uploaded files are persisted to disk (or could be swapped for object storage like S3/Azure Blob in production).
- **Backing services as attached resources** — MongoDB is treated as an attached resource accessible via a URI, allowing it to be swapped between local, containerised, or managed cloud instances without code changes.
- **Separation of concerns** — Backend, frontend, and static assets are organised into distinct directories, supporting independent deployment in container-based environments.

---

## 🔮 Future Improvements

- [ ] **Containerisation** — Dockerfile and `docker-compose.yml` for one-command local setup
- [ ] **Cloud storage migration** — Replace local `uploads/` with AWS S3 or Azure Blob Storage
- [ ] **User authentication** — JWT-based auth so users can manage their own galleries
- [ ] **Image deduplication** — Hash-based duplicate filename handling on upload
- [ ] **CI/CD pipeline** — GitHub Actions workflow for automated testing and deployment
- [ ] **Search & tagging** — Full-text search across image metadata

---

## 📚 Module Context

This project was developed for the **Cloud Native Development** module as part of the BSc Computing Systems programme. It demonstrates the practical application of cloud-native architecture principles, NoSQL data modelling, and modern web development practices.

---

## 👤 Author

**Farhan Bin Hossain**  
[GitHub](https://github.com/farhanbin65)

---

## 📄 License

This project is for educational purposes as part of university coursework.