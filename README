# Yoohoo

**Real videos. Real people.**

Yoohoo is a video-sharing platform designed to help people discover and share authentic human-made content. It integrates AI-powered video analysis to identify potentially AI-generated videos and applies a detection threshold before allowing videos to be published.

The project combines a modern web interface with a Python backend, video analysis, cloud storage, and database persistence.

## Features

- **Video uploads** — Upload videos with titles and metadata.
- **AI video detection** — Analyze uploaded videos using NVIDIA's synthetic video detector.
- **Automated review decisions** — Apply a configurable detection threshold to determine whether a video passes or is rejected.
- **Video discovery** — Browse available videos through the community feed.
- **Video storage** — Store approved video files using Supabase Storage.
- **Database persistence** — Save video metadata and analysis results in PostgreSQL through Supabase.
- **Responsive interface** — Access Yoohoo through a modern web interface.
- **User feedback** — Provide feedback when video analysis rejects an upload.

## ️ Tech Stack

| Component            | Technology                      |
| -------------------- | ------------------------------- |
| Frontend framework   | Next.js                         |
| Programming language | TypeScript                      |
| Styling              | Tailwind CSS                    |
| Icons                | Lucide React                    |
| Backend framework    | FastAPI                         |
| Backend language     | Python                          |
| Video processing     | OpenCV                          |
| AI detection         | NVIDIA synthetic video detector |
| Database             | PostgreSQL via Supabase         |
| File storage         | Supabase Storage                |
| Frontend deployment  | Vercel                          |
| Backend deployment   | Render                          |

## ️ Architecture

```text
User
  |
  v
Next.js Frontend
  |
  | HTTP requests
  v
FastAPI Backend
  |
  +----> OpenCV Video Inspection
  |
  +----> NVIDIA AI Video Detector
  |
  +----> Supabase Storage
  |
  +----> Supabase PostgreSQL
  |
  v
Analysis Result
  |
  v
Frontend Displays Feedback
```

The frontend communicates with the backend through HTTP requests. Uploaded videos are validated and analyzed before the backend decides whether they can proceed to publication. Videos that pass the configured threshold are stored, and their metadata and analysis results are recorded in the database.

## Live Demo

- **Frontend:** https://frontend-six-fawn-29.vercel.app/
- **Backend API:** https://yoohoo-backend.onrender.com
- **Health check:** https://yoohoo-backend.onrender.com/health

## Project Structure

The frontend and backend are maintained in separate repositories.

### Frontend

```text
yoohoo/
├── public/
│   └── sounds/
├── src/
│   ├── app/
│   │   ├── page.tsx
│   │   ├── layout.tsx
│   │   └── upload/
│   ├── components/
│   └── lib/
├── package.json
├── next.config.ts
└── README.md
```

### Backend

```text
human-tube-backend/
├── app/
│   ├── routes/
│   │   └── videos.py
│   └── storage.py
├── vendor/
│   └── nvidia-synthetic-video-detector/
│       └── scripts/
│           └── v1/
│               └── synthetic-video-detector.py
├── main.py
└── requirements.txt
```

_The structure above illustrates the main components; your actual files and configuration may differ._

## Getting Started

### Prerequisites

Install the following before running the project:

- Node.js and npm
- Python 3.10 or a compatible version supported by your backend dependencies
- A Supabase project
- An NVIDIA API key with access to the configured video detection service

### 1. Clone the frontend

```bash
git clone https://github.com/princekrazy/yoohoo.git
cd yoohoo
```

Install dependencies:

```bash
npm install
```

### 2. Configure the frontend

Create a `.env.local` file in the frontend root:

```env
NEXT_PUBLIC_API_BASE_URL=https://yoohoo-backend.onrender.com
NEXT_PUBLIC_API_MODE=real
```

The API mode should match the configuration supported by the frontend API client. Use the mock mode if you want to develop against mock data without contacting the backend.

**Important:** Variables prefixed with `NEXT_PUBLIC_` are exposed to browser-side code. Never place API keys, database credentials, or other secrets in them.

### 3. Run the frontend

```bash
npm run dev
```

Open http://localhost:3000 in your browser.

To create a production build:

```bash
npm run build
```

### 4. Set up the backend

Clone the backend repository separately:

```bash
git clone https://github.com/princekrazy/human-tube-backend.git
cd human-tube-backend
```

Create and activate a virtual environment.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the backend dependencies:

```powershell
pip install -r requirements.txt
```

Create a backend `.env` file containing the credentials required by your configuration:

```env
NVIDIA_API_KEY=your_nvidia_api_key
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_key
```

Use the exact environment variable names expected by your `app/storage.py` implementation. Keep this file private and never commit secrets to GitHub.

Start the FastAPI server using the module that defines your `app` object. For example, if it is `main.py`:

```bash
uvicorn main:app --reload
```

The local API will typically be available at http://localhost:8000.

## API

The backend currently includes the following documented endpoints:

| Method | Endpoint              | Purpose                                             |
| ------ | --------------------- | --------------------------------------------------- |
| `GET`  | `/health`             | Check backend health                                |
| `GET`  | `/api/videos`         | Retrieve videos through the registered video router |
| `POST` | `/api/videos/analyze` | Upload and analyze a video                          |

The video listing endpoint is provided by the registered video router. Additional endpoints may be available depending on its implementation.

### Video analysis workflow

1. The frontend submits a video file and its title.
2. The backend validates the file extension and enforces a 100 MB size limit.
3. OpenCV inspects the video and samples frames.
4. The NVIDIA detector analyzes the MP4 file.
5. The backend calculates the mean detection probability.
6. The result is compared with the configured threshold of `0.30`.
7. Videos that pass the threshold are stored in Supabase Storage, and their metadata is inserted into the database.
8. Videos that exceed the threshold are rejected.

**Detection limitations:** AI-generated video detection is probabilistic and can produce false positives or false negatives. Passing the threshold does not prove that a video was created by a human, and a high score is not definitive proof that a video is synthetic.

## ️ Deployment

### Frontend — Vercel

1. Import the frontend repository into Vercel.
2. Set `NEXT_PUBLIC_API_BASE_URL` to the deployed backend URL.
3. Set `NEXT_PUBLIC_API_MODE` to the intended API mode.
4. Deploy the application.

### Backend — Render

1. Connect the backend repository to Render.
2. Configure the Python build and start commands.
3. Add the required environment variables through the Render dashboard.
4. Deploy and verify the `/health` endpoint.
5. Configure FastAPI CORS middleware to allow the production frontend origin.

For example, the production origin should be configured without a trailing slash:

```python
"https://frontend-six-fawn-29.vercel.app"
```

Never expose backend secrets through frontend environment variables.

## Security and Data Handling

- Keep API keys and database credentials in backend environment variables.
- Restrict CORS to trusted frontend origins in production.
- Validate uploaded files and enforce upload-size limits.
- Avoid exposing sensitive diagnostic information to public clients.
- Ensure Supabase database permissions and storage policies are appropriately configured.
- Delete both stored video objects and corresponding database records when cleaning up test data.
- Review the detection and publication policy before using the service for real user uploads.

## Development

Before submitting frontend changes, run:

```bash
npm run build
```

Test the following workflows:

- Loading the video feed.
- Uploading a valid MP4 file.
- Handling unsupported file formats.
- Displaying analysis results and rejection feedback.
- Handling backend errors and unavailable services.
- Confirming that approved videos appear in the feed.

## ️ Future Improvements

Potential next steps include:

- User accounts and creator profiles.
- Video search and category filtering.
- Likes, comments, and sharing.
- Pagination and improved feed performance.
- Video playback and thumbnail generation.
- Better provenance signals and human review workflows.
- Improved monitoring, upload progress, and error reporting.

## License

No license has been specified yet. Add a `LICENSE` file before distributing the project under an open-source license.

---

**Yoohoo — Real videos. Real people.**
