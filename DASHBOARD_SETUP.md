# 🚀 Dashboard Setup Guide

Follow these steps to get your GEM dashboard live on GitHub Pages.

## Step 1: Push to GitHub

If you haven't already, push your code to GitHub:

```bash
# Initialize git (if not already done)
git init
git add .
git commit -m "Initial commit with dashboard"

# Add your GitHub repository
git remote add origin https://github.com/yourusername/GEM.git

# Push to GitHub
git push -u origin main
```

## Step 2: Enable GitHub Pages

1. Go to your repository on GitHub
2. Click **Settings** (top menu)
3. Scroll down and click **Pages** (left sidebar)
4. Under "Build and deployment":
   - **Source**: Deploy from a branch
   - **Branch**: Select `main` → Select `/docs` folder
   - Click **Save**

5. Wait 1-2 minutes for GitHub to build your site

## Step 3: Access Your Dashboard

Your dashboard will be live at:

```
https://yourusername.github.io/GEM/
```

Replace `yourusername` with your actual GitHub username.

## Step 4: Verify Automatic Updates

1. Go to the **Actions** tab in your GitHub repository
2. You should see the "Update GEM Dashboard" workflow
3. This workflow runs automatically on the 1st of every month at 9:00 AM UTC
4. You can also click **Run workflow** to trigger a manual update

## What Gets Updated Automatically?

- ✅ Latest market data (from Yahoo Finance)
- ✅ Current momentum calculations
- ✅ Trading signal (RISK-ON/RISK-OFF)
- ✅ Asset selection recommendation
- ✅ Historical signal data

## Manual Dashboard Update

If you want to update the dashboard manually (without waiting for the scheduled run):

```bash
# Activate virtual environment
source .venv/bin/activate

# Generate new data
python generate_dashboard_data.py

# Commit and push
git add docs/data.json
git commit -m "Update dashboard data"
git push
```

The dashboard will update within 1-2 minutes.

## Customization

### Change Update Frequency

Edit `.github/workflows/update-dashboard.yml`:

```yaml
on:
  schedule:
    # Daily at 9 AM UTC
    - cron: '0 9 * * *'
    
    # Weekly on Monday at 9 AM UTC
    - cron: '0 9 * * 1'
    
    # Monthly on the 1st at 9 AM UTC (current)
    - cron: '0 9 1 * *'
```

### Customize Dashboard Appearance

Edit `docs/index.html` to change:
- Colors and styling (CSS in `<style>` section)
- Layout and structure (HTML in `<body>` section)
- Data display logic (JavaScript in `<script>` section)

## Troubleshooting

### Dashboard not updating?

1. Check the **Actions** tab for failed workflows
2. Verify GitHub Pages is enabled in Settings → Pages
3. Make sure the `/docs` folder exists in your `main` branch

### "404 Not Found" error?

1. Wait 2-3 minutes after enabling GitHub Pages
2. Check that you're using the correct URL
3. Verify the `index.html` file exists in the `docs/` folder

### Data showing old information?

1. Run the workflow manually: Actions → Update GEM Dashboard → Run workflow
2. Check that the workflow completed successfully
3. Force refresh your browser (Ctrl+Shift+R or Cmd+Shift+R)

## Privacy & Security

- ✅ No API keys or secrets needed
- ✅ All data is public (from Yahoo Finance)
- ✅ Dashboard runs entirely in the browser
- ✅ No server-side code or database

## Need Help?

If you encounter issues:
1. Check the GitHub Actions logs
2. Verify your Python dependencies are correct
3. Test the dashboard generation locally first
4. Open an issue on GitHub

---

Enjoy your automated GEM dashboard! 🎉
