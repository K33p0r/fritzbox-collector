# Tibber Integration - Quick Start Guide

Get your Tibber Pulse IR data into the FritzBox Collector in 5 minutes!

## Prerequisites

✅ Tibber account with active subscription  
✅ Tibber Pulse IR device installed and connected  
✅ MariaDB/MySQL database available  
✅ Docker installed (recommended)  

## Step 1: Get Your Tibber Token (2 minutes)

1. Go to https://developer.tibber.com/settings/access-token
2. Log in with your Tibber account
3. Click "Create a token"
4. **Copy the token** - you won't see it again!

## Step 2: Test Your Connection (1 minute)

```bash
# Install dependencies (if not using Docker)
pip3 install gql[all] aiohttp

# Test your token
python3 test_tibber_connection.py YOUR_TOKEN_HERE
```

✅ If successful, you'll see your account info and homes!

## Step 3: Deploy with Docker Compose (2 minutes)

```bash
# 1. Edit docker-compose.yml
# Uncomment and set TIBBER_TOKEN=your_token_here

# 2. Start everything
docker-compose up -d

# 3. Check logs
docker-compose logs -f fritzbox-collector
```

Look for: `✅ Tibber integration enabled`

## Step 4: Import Grafana Dashboard (30 seconds)

1. Open Grafana: http://localhost:3000
2. Login (admin/change_this_password)
3. Go to Dashboards → Import
4. Upload `grafana-dashboard-tibber.json`
5. Select MariaDB data source
6. Click Import

🎉 **Done!** You should see your energy data!

---

## Alternative: Docker Run

```bash
docker run -d --restart=unless-stopped \
  -e FRITZBOX_HOST=192.168.178.1 \
  -e FRITZBOX_USER=your_user \
  -e FRITZBOX_PASSWORD=your_password \
  -e SQL_HOST=your_db_host \
  -e SQL_USER=db_user \
  -e SQL_PASSWORD=db_password \
  -e SQL_DB=fritzbox \
  -e TIBBER_TOKEN=your_tibber_token \
  -v /path/to/config:/config \
  fritzbox-collector
```

---

## Verification Checklist

After deployment, verify:

- [ ] Container is running: `docker ps`
- [ ] No errors in logs: `docker logs fritzbox-collector`
- [ ] Database table exists: `SELECT * FROM tibber_energy_data LIMIT 1;`
- [ ] Data is being collected (check logs for "Fetched X records")
- [ ] Grafana dashboard shows data

---

## Troubleshooting

### "Cannot fetch Tibber data: TIBBER_TOKEN not set"
➡️ Set the TIBBER_TOKEN environment variable in docker-compose.yml or docker run command

### "Unauthorized" or "Invalid token"
➡️ Generate a new token at https://developer.tibber.com/settings/access-token

### No data in Grafana
➡️ Wait 1 hour for first collection (default TIBBER_INTERVAL=3600)  
➡️ Check logs: `docker logs -f fritzbox-collector`  
➡️ Verify Tibber Pulse IR is online in Tibber app

### Connection test fails
➡️ Check internet connectivity  
➡️ Verify firewall allows connections to api.tibber.com  
➡️ Ensure token is copied correctly (no extra spaces)

---

## Next Steps

📚 **Read the full guides:**
- [TIBBER_SETUP.md](TIBBER_SETUP.md) - Complete setup guide
- [GRAFANA_QUERIES.md](GRAFANA_QUERIES.md) - Custom query examples
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - Technical details

⚙️ **Customize your setup:**
- Adjust TIBBER_INTERVAL (default: 3600s = 1 hour)
- Create custom Grafana panels
- Set up alerts for high consumption

🔔 **Enable notifications:**
- Add DISCORD_WEBHOOK for error alerts
- Add TELEGRAM_TOKEN and TELEGRAM_CHATID for notifications

---

## Configuration Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| TIBBER_TOKEN | Yes* | - | Your personal access token |
| TIBBER_INTERVAL | No | 3600 | Collection interval in seconds |
| FRITZBOX_HOST | Yes | - | FritzBox IP address |
| SQL_HOST | Yes | - | Database host |
| SQL_USER | Yes | - | Database username |
| SQL_PASSWORD | Yes | - | Database password |
| SQL_DB | Yes | - | Database name |

*Only required if you want Tibber integration

---

## Support

- 📖 Full documentation in this repository
- 🐛 Issues: https://github.com/K33p0r/fritzbox-collector/issues
- 📧 Tibber Support: https://tibber.com/support

---

**Estimated Time to Production:** 5 minutes  
**Difficulty:** Easy  
**Last Updated:** October 2025
