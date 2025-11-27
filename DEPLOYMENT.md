# Deploying to Render

## Prerequisites
1. Create a GitHub repository for your project
2. Sign up for a Render account at https://render.com

## Steps to Deploy

### 1. Prepare Your Repository
1. Push your code to GitHub:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/yourusername/your-repo-name.git
   git push -u origin main
   ```

### 2. Deploy to Render
1. Go to https://dashboard.render.com
2. Click "New+" and select "Web Service"
3. Connect your GitHub repository
4. Configure the service:
   - Name: agri-advisor-backend
   - Region: Choose the closest region to your users
   - Branch: main
   - Root Directory: backend
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Plan: Free (or choose a paid plan for production)

### 3. Configure Environment Variables
In Render dashboard, go to your service settings and add these environment variables:
- NEO4J_URI=your_neo4j_uri
- NEO4J_USERNAME=your_neo4j_username
- NEO4J_PASSWORD=your_neo4j_password
- NEO4J_DATABASE=neo4j
- OPENAI_API_KEY=your_openai_api_key
- GROQ_API_KEY=your_groq_api_key
- INDIAN_WEATHER_API_KEY=your_weather_api_key
- AGMARKNET_API_KEY=your_agmarknet_api_key

**⚠️ Security Note:** Never commit API keys to version control. Always use Render's environment variable configuration instead.

### 4. Update Frontend Configuration
After deployment, update the `public/config.json` file in your frontend:
```json
{
  "apiBaseUrl": "https://your-render-service-url.onrender.com",
  "comments": {
    "development": "For development, use http://localhost:8000",
    "production": "For production deployment, replace with your deployed backend URL e.g., https://your-app.onrender.com",
    "mobile": "For mobile apps on the same network, use your computer's IP address e.g., http://192.168.1.16:8000"
  }
}
```

### 5. Deploy Frontend
For frontend deployment on Render:
1. Create another Web Service
2. Root Directory: . (root of your project)
3. Build Command: `npm install && npm run build`
4. Publish Directory: dist

## Notes
- Render automatically provides SSL certificates
- Free tier services sleep after 15 minutes of inactivity
- First build may take several minutes
- You can monitor logs in the Render dashboard

## 🔐 Security Best Practices for Deployment

### Environment Variables
When deploying to Render, always use their environment variable configuration rather than committing `.env` files:

1. **In Render Dashboard:**
   - Go to your service
   - Click "Environment" tab
   - Add each required variable:
     - `NEO4J_URI` = your Neo4j connection string
     - `NEO4J_USERNAME` = your Neo4j username
     - `NEO4J_PASSWORD` = your Neo4j password
     - `OPENAI_API_KEY` = your OpenAI API key
     - etc.

2. **Never store secrets in:**
   - Source code
   - Configuration files in version control
   - Client-side JavaScript
   - Build scripts

### API Key Management
1. **Use separate keys for development and production**
2. **Enable key rotation policies**
3. **Monitor API usage for anomalies**
4. **Restrict key permissions to minimum required**
5. **Use key expiration when supported by the service**

### Verification
After deployment, verify that:
1. Environment variables are properly set in Render dashboard
2. No sensitive data is visible in your GitHub repository
3. Application functions correctly with the configured environment variables