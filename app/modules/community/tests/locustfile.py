import re

from locust import HttpUser, between, task

from core.environment.host import get_host_for_locust_testing


class CommunityUser(HttpUser):

    host = get_host_for_locust_testing()
    wait_time = between(1, 3)
    community_slug = None

    def on_start(self):
        """Obtiene un slug válido lo cachea."""
        response = self.client.get("/community/list")
        if response.status_code == 200:
            pattern = r'href="/community/([a-z0-9_-]+)"'
            matches = re.findall(pattern, response.text)
            valid_slugs = [slug for slug in matches if slug not in ["list", "create", "manage"]]
            if valid_slugs:
                self.community_slug = valid_slugs[0]

    @task
    def list_communities(self):
        """
        Test de carga para el listado de comunidades.
        Endpoint: GET /community/list
        """
        response = self.client.get("/community/list")
        if response.status_code != 200:
            print(f"Error en list_communities: status_code={response.status_code}")

    @task
    def view_community_with_datasets(self):
        """
        Test de carga para la vista de una comunidad individual.
        Endpoint: GET /community/<slug>
        Usa el slug cacheado
        """
        if not self.community_slug:
            print("Error: No hay slug disponible")
            return

        response = self.client.get(f"/community/{self.community_slug}", name="/community/[slug]")
        if response.status_code != 200:
            print(f"Error en view_community: slug={self.community_slug}, status_code={response.status_code}")
