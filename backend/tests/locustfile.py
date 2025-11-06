"""
Load testing with Locust.
Simulates concurrent ranking requests.

TODO: Implement for Days 13-14 (Testing & Delivery)

Usage:
    locust -f locustfile.py --host=http://localhost:8000
"""

from locust import HttpUser, task, between


class RankingUser(HttpUser):
    """Simulated user performing ranking requests."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between requests

    @task(3)
    def rank_candidates(self):
        """Test ranking endpoint."""
        # TODO: Implement load test for /api/jobs/rank
        pass

    @task(1)
    def health_check(self):
        """Test health endpoint."""
        self.client.get("/health")

    @task(1)
    def get_rankings(self):
        """Test get rankings endpoint."""
        # TODO: Implement load test for /api/jobs/{job_id}/rankings
        pass
