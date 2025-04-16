import jwt

def verify_jwt(token):
    try:
        decoded = jwt.decode(token, "your-256-bit-secret", algorithms=["HS256"],audience="video-stream-service")
        print("JWT is valid:", decoded)
        return True
    except jwt.exceptions.InvalidTokenError as e:
        print("JWT is invalid:", str(e))
        return False

# 测试JWT
test_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjbGllbnRfaWQiOiJncmFkaW8tY2xpZW50Iiwic2NvcGVzIjpbInZpZGVvX3N0cmVhbSJdLCJleHAiOjE3NDQ2MTgzMTIsImlzcyI6ImZhY2UtcmVjb2duaXRpb24tYXV0aCIsImF1ZCI6InZpZGVvLXN0cmVhbS1zZXJ2aWNlIiwiaWF0IjoxNzQ0NjE2NTEyfQ._U3UrRVyfXrRChpAZfBSStm8IAOPh2NE0XMAms9Sk10"
verify_jwt(test_token)
