import datetime
import os
import sys


def ensure_project_path():
    current = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    return project_root


def main():
    username = "testuser3"
    user_id = 8903
    role = "normal"
    expires_in_hours = -1

    ensure_project_path()

    from src.authentication import JWTUtils

    secret = os.getenv("JWT_SECRET_KEY", "fallback_secret_key")
    jwt_utils = JWTUtils(secret_key=secret)
    token = jwt_utils.generate_token(
        {
            "user_id": user_id,
            "username": username,
            "role": role,
        },
        expires_in_hours=expires_in_hours,
    )

    payload = jwt_utils.decode_without_exp_verification(token) or {}
    now_ts = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    exp_ts = payload.get("exp")
    expired_seconds = (now_ts - exp_ts) if isinstance(exp_ts, int) else None

    print("PASS generate expired jwt")
    print(f"USERNAME={username}")
    print(f"USER_ID={user_id}")
    print(f"ROLE={role}")
    print(f"NOW_TS={now_ts}")
    print(f"EXP_TS={exp_ts}")
    print(f"EXPIRED_SECONDS={expired_seconds}")
    print(f"TOKEN={token}")


if __name__ == "__main__":
    main()
