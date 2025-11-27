# 🔐 Security Policy

## 🛡️ Environment Variables and API Keys Security

### ⚠️ Critical Security Notice
**Never commit API keys, passwords, or other sensitive credentials to version control.** This is a critical security practice that must be followed at all times.

### 📁 Files That Should Never Be Committed
The following files contain sensitive information and are automatically excluded from version control via `.gitignore`:

- `.env` - Contains all API keys and secrets
- `.env.local` - Local environment overrides
- `.env.*.local` - Environment-specific local overrides
- Any file matching the pattern `.env*`

### 📋 Required Environment Variables
Your `.env` file should contain the following variables:

```bash
# Neo4j AuraDB Configuration
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USERNAME=your-username
NEO4J_PASSWORD=your-password
NEO4J_DATABASE=neo4j

# OpenAI API Key
OPENAI_API_KEY=your-secret-api-key

# Groq API Key
GROQ_API_KEY=your-secret-api-key

# Indian Weather API Key
INDIAN_WEATHER_API_KEY=your-secret-api-key

# Agmarknet API Key
AGMARKNET_API_KEY=your-secret-api-key
```

### 🔧 Setting Up Your Environment

1. **Copy the template:**
   ```bash
   cd backend
   cp env_template.txt .env
   ```

2. **Edit `.env` with your actual credentials:**
   ```bash
   # Replace placeholder values with your actual credentials
   NEO4J_URI=neo4j+s://a351a54a.databases.neo4j.io
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=your-actual-password
   OPENAI_API_KEY=sk-your-actual-openai-api-key
   ```

3. **Verify .gitignore:**
   Ensure that `.env` is listed in your `.gitignore` file:
   ```gitignore
   # Environment variables files (CRITICAL: These contain API keys and secrets)
   .env
   .env.local
   .env.*.local
   ```

### 🚫 What NOT to Do
- ❌ Never commit `.env` files to version control
- ❌ Never share API keys in code comments or documentation
- ❌ Never hardcode credentials in source files
- ❌ Never use production keys in development environments
- ❌ Never store keys in client-side code

### ✅ What TO Do
- ✅ Always use environment variables for credentials
- ✅ Always keep `.env` in `.gitignore`
- ✅ Use different keys for development and production
- ✅ Rotate API keys regularly
- ✅ Use key management services in production
- ✅ Document required environment variables in template files

### 🔄 Best Practices
1. **Use template files:** Always provide `env_template.txt` or similar for required variables
2. **Document requirements:** Clearly document all required environment variables
3. **Validate on startup:** Check for required environment variables when the application starts
4. **Use strong keys:** Generate strong, random API keys
5. **Limit permissions:** Use API keys with minimal required permissions
6. **Monitor usage:** Regularly check API key usage for suspicious activity

### 🚨 If You Accidentally Commit Keys
If you accidentally commit sensitive credentials:

1. **Immediately revoke the keys** from the respective service
2. **Generate new keys** with the service provider
3. **Update your `.env` file** with the new keys
4. **Remove the commit** from history if possible:
   ```bash
   git reset --soft HEAD~1
   git commit -m "Remove accidental credential commit"
   ```
5. **Notify relevant parties** if the keys were exposed publicly

### 📚 Additional Resources
- [Git Secrets](https://github.com/awslabs/git-secrets) - Prevents you from committing secrets
- [TruffleHog](https://github.com/trufflesecurity/truffleHog) - Scans for secrets in git repositories
- [GitHub Security Guide](https://docs.github.com/en/github/authenticating-to-github/keeping-your-account-and-data-secure)