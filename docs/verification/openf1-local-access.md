# Configure OpenF1 access for APEX

Historical requests normally work without a subscription. During a live session
OpenF1 can restrict historical access to authenticated users. APEX received
that restriction during the R041 driving-data acquisition.

For authenticated access, use **Get access** on the
[OpenF1 account page](https://openf1.org/account). OpenF1 emails a username and
password after signup. Its
[authentication guide](https://openf1.org/auth.html) describes exchanging them
for a bearer token that expires after one hour.

Open a terminal in the APEX repository and run the following command. Choose
fresh snapshot and output paths on each acquisition attempt.

```powershell
.\.venv\Scripts\python.exe research/scripts/acquire_compound_driving.py --sign-in --snapshots .cache/r041-driving-auth-01 --output .cache/r041-driving-auth-01-data.json
```

Enter the OpenF1 username at the prompt. The password prompt hides the password.
The downloader keeps the resulting token in memory for that process. Credentials
and authorization headers are omitted from saved snapshots and Git files.
The normal rate limits and immutable response checks still apply.

An existing token can instead be supplied through a process environment
variable. Pass its name with `--token-env OPENF1_ACCESS_TOKEN`. Avoid placing
secret values in command arguments or committing them to repository files.

Without a subscription, retry after the live-session restriction ends using
the same command with `--sign-in` omitted. No sign-in prompt will appear.
Saved HTTP 401 receipts remain immutable, so use a fresh snapshot directory.

The output is a new driving-data artifact. Its coverage and prediction results
must be audited before it replaces an experiment input. Successful acquisition
alone cannot close R041.
