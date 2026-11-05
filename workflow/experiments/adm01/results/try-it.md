# Try it yourself

1. Start Postgres: `docker run -d --name adm01-pg -e POSTGRES_USER=learnswe -e POSTGRES_DB=learnswe -e POSTGRES_PASSWORD=<choose> -p 127.0.0.1:55432:5432 postgres:16`
2. In PowerShell set `$env:TEA01_TEST_DATABASE_URL = "postgresql+psycopg://learnswe:<password>@127.0.0.1:55432/learnswe"`
3. Grade one arm (from the repo root):
   `python workflow\experiments\adm01\tools\grade_arm.py --arm-dir ..\adm01-wt\H3 --frozen-dir ..\adm01-frozen-wt\src\backend\tests --files adm01_helpers.py test_adm01_report.py test_adm01_hooks.py --expected 153`
4. Expected: A 152/153, H1/H2/H3 153/153.
5. Open `workflow\experiments\adm01\results\comparison.html`.
6. Remove the container when done: `docker rm -f adm01-pg`.
