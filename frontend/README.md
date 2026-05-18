## **📖 Overview**

The **Logara AI Frontend** is a modern, responsive, and intuitive web dashboard designed for the Logara AI observability platform. It transforms complex log data into actionable, AI-powered insights. By leveraging semantic log visualization and modern monitoring workflows, this dashboard empowers engineers to identify, analyze, and resolve system issues with unprecedented speed and clarity.

## **🚀 Features**

* **🔍 Semantic Search Interface:** Query logs using natural language, powered by underlying vector databases.  
* **📊 Real-time Log Visualization:** Dynamic charts and graphs for immediate system pulse monitoring.  
* **🧠 AI-Powered Insights:** Automated anomaly detection and root cause analysis summaries.  
* **🚨 Error Analysis Workflows:** Streamlined paths from error identification to resolution.  
* **📱 Responsive UI:** Fully optimized experience across desktop and mobile devices.  
* **⚡ Future-Ready Architecture:** Built for scale, speed, and seamless integration with the Logara AI backend.

## **🛠️ Tech Stack**

This project is built with a modern, high-performance web stack:

| Technology | Description |
| :---- | :---- |
| **[React](https://reactjs.org/)** | UI Component Library |
| [**Vite**](https://vitejs.dev/) | Next Generation Frontend Tooling |
| [**JavaScript (ES6+)**](https://developer.mozilla.org/en-US/docs/Web/JavaScript) | Core Language |
| [**TailwindCSS**](https://tailwindcss.com/) | Utility-First CSS Framework |

*Note: This frontend is designed to integrate seamlessly with our **FastAPI** backend and **Qdrant** vector database.*

## **📂 Project Structure**

frontend/  
├── public/               \# Static assets  
├── src/  
│   ├── assets/           \# Images, icons, etc.  
│   ├── components/       \# Reusable UI components  
│   ├── pages/            \# Dashboard views  
│   ├── services/         \# API integration (FastAPI)  
│   ├── App.jsx           \# Main application component  
│   └── main.jsx          \# Application entry point  
├── .env.example          \# Example environment variables  
├── index.html            \# Main HTML file  
├── package.json          \# Dependencies and scripts  
├── tailwind.config.js    \# Tailwind configuration  
└── vite.config.js        \# Vite configuration

## **⚙️ Local Development Setup**

Follow these steps to get the Logara AI dashboard running locally.

### **Prerequisites**

* [Node.js](https://nodejs.org/) (v16 or higher recommended)  
* npm (or yarn/pnpm)

### **Installation**

1. **Clone the repository** (if you haven't already):  
   git clone \<repository-url\>  
   cd frontend

2. **Install dependencies:**  
   npm install

### **Environment Configuration**

1. Copy the example environment file:  
   cp .env.example .env

2. Update .env with your local settings (e.g., API endpoint URLs).

### **Running the Development Server**

Start the Vite development server with hot-module replacement (HMR):

npm run dev

The application will typically be available at http://localhost:5173/.

## **🏗️ Build Instructions**

To build the application for production:

npm run build

This will generate a dist/ directory containing the optimized, minified static files ready for deployment. To preview the production build locally:

npm run preview

## **🗺️ Future Roadmap**

We are constantly iterating to build the ultimate observability dashboard. Upcoming features include:

* **\[ \] Live Streaming Logs:** Real-time, tail-like log viewing within the browser.  
* **\[ \] "Explain Error" Dashboard:** Deeper AI integration for instantaneous error decoding.  
* **\[ \] Advanced Filtering:** Complex query building and saved filter states.  
* **\[ \] Dark Mode Enhancements:** Further refinement of our dark theme for late-night debugging.  
* **\[ \] OpenTelemetry Integration:** Native support for visualizing distributed traces.

## **🤝 Contributing**

We welcome contributions from the community\! Whether you want to improve the UI/UX, add new features, or fix bugs, your help is appreciated.

Please ensure your code adheres to the existing style and that you open an issue to discuss major changes before submitting a pull request.

## **📄 License**

This project is licensed under the [MIT License](http://docs.google.com/LICENSE) \- see the LICENSE file for details.