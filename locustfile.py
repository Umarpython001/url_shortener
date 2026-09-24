import random

from locust import HttpUser, task, between


class Shortener(HttpUser):
    wait_time = between(0.1, 0.5)

    # shared across all simulated users so redirects hit real rows
    codes = []

    def on_start(self):
        for _ in range(5):
            self._create()

    def _create(self):
        n = random.randint(0, 10**9)
        r = self.client.post(
            "/shorten",
            params={"provided_long_url": f"https://example.com/page/{n}"},
            name="/shorten",
        )
        if r.status_code == 201:
            Shortener.codes.append(r.json()["code"])

    # roughly 95% reads, 5% writes
    @task(19)
    def redirect(self):
        if not Shortener.codes:
            return
        code = random.choice(Shortener.codes)
        # allow_redirects=False so Locust doesn't follow the 302 and
        # start load testing example.com
        self.client.get(
            f"/shortener/{code}",
            allow_redirects=False,
            name="/shortener/[code]",
        )

    @task(1)
    def create(self):
        self._create()