from locust import HttpUser, task, between
import os
import uuid
import time
import random

MOCK_QUESTIONS = [
    {
        "q": f"Mock Question {i}?",
        "opts": ["A", "B", "C", "D"],
        "ans": 0,
        "topic": "General Mock Theme"
    } for i in range(25)
]

MOCK_ANSWERS = [
    {"q_index": i, "selected": 0} for i in range(25)
]

class StaffUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Register a new active user to avoid concurrency issues with shared credentials and ensure a fresh state."""
        self.username = f"staff_{uuid.uuid4().hex[:8]}"
        self.password = f"LoadTest-{uuid.uuid4().hex}"
        self.email = f"{self.username}@rescue1122.gov.pk"
        
        # Register
        self.client.post("/api/auth/register", json={
            "email": self.email,
            "username": self.username,
            "password": self.password,
            "full_name": f"Load Test User {self.username}",
            "designation": "Firefighter",
            "district": "Lahore"
        })
        
        # Login
        response = self.client.post("/api/auth/login", data={
            "username": self.username,
            "password": self.password
        })
        if response.status_code == 200:
            self.token = response.json().get("access_token")
            self.client.headers.update({"Authorization": f"Bearer {self.token}"})

    @task(3)
    def generate_test(self):
        self.client.post("/api/test/generate", json={
            "topic_id": "fire_basics",
            "designation": "Firefighter"
        })

    @task(3)
    def submit_test(self):
        self.client.post("/api/test/submit", json={
            "topic_id": "fire_basics",
            "topic_label": "Fire Chemistry",
            "questions": MOCK_QUESTIONS,
            "answers": MOCK_ANSWERS,
            "started_at": "2024-01-01T10:00:00Z",
            "time_taken_seconds": random.randint(300, 1800)
        })

    @task(2)
    def history(self):
        self.client.get("/api/test/history")


class AdminUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Login with admin credentials supplied by the operator."""
        self.username = os.getenv("LOCUST_ADMIN_USERNAME", "admin")
        self.password = os.getenv("LOCUST_ADMIN_PASSWORD")
        if not self.password:
            raise RuntimeError("Set LOCUST_ADMIN_PASSWORD before running admin load tests.")
        
        response = self.client.post("/api/auth/login", data={
            "username": self.username,
            "password": self.password
        })
        if response.status_code == 200:
            self.token = response.json().get("access_token")
            self.client.headers.update({"Authorization": f"Bearer {self.token}"})

    @task(2)
    def stats(self):
        self.client.get("/api/admin/stats")

    @task(2)
    def attempts(self):
        self.client.get("/api/admin/attempts")

    @task(1)
    def leaderboard(self):
        self.client.get("/api/admin/leaderboard")
