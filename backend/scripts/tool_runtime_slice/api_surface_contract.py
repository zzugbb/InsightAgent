import json

import check_api_surface


class ApiSurfaceContractMixin:
    def test_api_surface_baseline_matches_current_openapi(self) -> None:
        baseline = json.loads(check_api_surface.BASELINE_PATH.read_text())
        current = check_api_surface.current_manifest()
        self.assertEqual(check_api_surface.differences(baseline, current), [])
        self.assertGreaterEqual(len(current["operations"]), 40)

    def test_api_surface_detects_schema_property_named_title(self) -> None:
        original = {
            "info": {"version": "0.1.0"},
            "paths": {
                "/items": {
                    "get": {
                        "responses": {"200": {"description": "Success"}},
                    }
                }
            },
            "components": {
                "schemas": {
                    "Item": {"type": "object", "properties": {"title": {"type": "string"}}}
                }
            },
        }
        revised = json.loads(json.dumps(original))
        revised["components"]["schemas"]["Item"]["properties"]["title"]["type"] = "integer"
        self.assertEqual(
            check_api_surface.differences(
                check_api_surface.build_manifest(original),
                check_api_surface.build_manifest(revised),
            ),
            ["changed components: schemas.Item"],
        )

    def test_api_surface_detects_removed_route_and_schema_field_change(self) -> None:
        baseline = {
            "schema_version": 1,
            "api_version": "0.1.0",
            "openapi_version": "3.1.0",
            "operations": {"GET /items": "old-fingerprint"},
            "components": {"schemas.Item": "old-schema"},
        }
        current = {
            **baseline,
            "operations": {},
            "components": {"schemas.Item": "new-schema"},
        }
        self.assertEqual(
            check_api_surface.differences(baseline, current),
            ["removed operations: GET /items", "changed components: schemas.Item"],
        )
