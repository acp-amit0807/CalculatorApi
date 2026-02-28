import re

def sanitize_diff(diff):
    diff = re.sub(r'password\s*=\s*".*?"',
                  'password="***REDACTED***"',
                  diff,
                  flags=re.IGNORECASE)

    diff = re.sub(r'PRIVATE KEY.*?END PRIVATE KEY',
                  '***REDACTED KEY***',
                  diff,
                  flags=re.DOTALL)

    return diff