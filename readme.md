[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

You can receive API token for SAASU in 2 ways:

1. By providing `SAASU_LOGIN` and `SAASU_PASSWORD`, and looking into application logs
2. Also you can query for required `refresh token` the API directly, for this you should execute following command in terminal:
```
curl -XPOST -H "Content-Type: application/json" -d '{"username": "<USER>", "password": "<PASSWORD>", "grant_type": "password", "scope": "full"}' https://api.saasu.com/authorisation/token
```
(don't forget to replace `<USER>` and `<PASSWORD>` with actual values), in the response you'll receive something like
```
{"access_token":"eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9",
"token_type":"Bearer",
"expires_in":10800,
"refresh_token":"eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9",
"scope":"fileid:12356"}
```
Now, copy value for `refresh_token` (without quotes) into configuration variable named `SAASU_REFRESH_TOKEN`, and your're ready to go!