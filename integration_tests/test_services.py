import concurrent.futures
import time
import unittest

import requests
import urllib3

SERVICE_B_URL = "https://localhost:5002/api/v1/equipment/cpe/"

# Disable warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class TestEquipmentActivation(unittest.TestCase):
    def test_configuration_task(self):
        equipment_id = "ABCDEF"
        url = SERVICE_B_URL + equipment_id
        payload = {
            "timeoutInSeconds": 14,
            "parameters": {"username": "admin", "password": "admin", "vlan": 534, "interfaces": [1, 2, 3, 4]},
        }

        response = requests.post(url, json=payload, verify=False)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("taskID", data)
        task_id = data["taskID"]

        status_url = url + "/task/" + task_id
        for _ in range(70):
            status_response = requests.get(status_url, verify=False)
            if status_response.status_code == 200:
                result = status_response.json()
                self.assertEqual(result.get("message"), "Completed")
                break
            time.sleep(1)
        else:
            self.fail("Task did not complete in expected time.")

    def test_invalid_equipment_id(self):
        invalid_id = "ABC"
        url = SERVICE_B_URL + invalid_id
        payload = {
            "timeoutInSeconds": 14,
            "parameters": {"username": "admin", "password": "admin", "vlan": 534, "interfaces": [1, 2, 3, 4]},
        }

        # POST should return 404 for an invalid equipment ID
        response = requests.post(url, json=payload, verify=False)
        self.assertEqual(response.status_code, 404)

        # GET task status for invalid equipment ID should also return 404
        task_id = "non-existent"
        response = requests.get(url + "/task/" + task_id, verify=False)
        self.assertEqual(response.status_code, 404)

    def test_missing_payload(self):
        # Valid equipment ID but payload is missing required fields
        equipment_id = "ABCDEF"
        url = SERVICE_B_URL + equipment_id
        response = requests.post(url, json={}, verify=False)
        self.assertEqual(response.status_code, 400)

    def test_non_existent_task(self):
        # Valid equipment ID but the task ID does not exist
        equipment_id = "ABCDEF"
        non_existent_task = "non-existent-task"
        url = SERVICE_B_URL + equipment_id + "/task/" + non_existent_task
        response = requests.get(url, verify=False)
        self.assertEqual(response.status_code, 404)

    def test_concurrent_tasks(self):
        equipment_id = "ABCDEF"
        url = SERVICE_B_URL + equipment_id
        payload = {
            "timeoutInSeconds": 14,
            "parameters": {"username": "admin", "password": "admin", "vlan": 534, "interfaces": [1, 2, 3, 4]},
        }
        num_tasks = 5
        task_ids = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_tasks) as executor:
            futures = [executor.submit(requests.post, url, json=payload, verify=False) for _ in range(num_tasks)]
            for future in concurrent.futures.as_completed(futures):
                response = future.result()
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertIn("taskID", data)
                task_ids.append(data["taskID"])

        for task_id in task_ids:
            status_url = url + "/task/" + task_id
            for _ in range(70):
                status_response = requests.get(status_url, verify=False)
                if status_response.status_code == 200:
                    result = status_response.json()
                    self.assertEqual(result.get("message"), "Completed")
                    break
                time.sleep(1)
            else:
                self.fail("Task {} did not complete in expected time.".format(task_id))


if __name__ == "__main__":
    unittest.main()
