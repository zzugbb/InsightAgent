from __future__ import annotations

from .context import *


class RegistrySourceFileDiagnosticsMixinPart1:
    def test_build_tool_registry_from_file_artifacts_merges_registry_source_diagnostics(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            child_file = Path(tmpdir) / "child-source-registry.json"
            missing_file = Path(tmpdir) / "missing-child-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_sources": ["search_suite"],
                    }
                ),
                encoding="utf-8",
            )
            child_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "provider_search": {
                                "template": "task_retrieve",
                                "label": "Provider Search",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "search_suite": {
                            "registry_file": str(child_file),
                        }
                    }
                )
            )

            artifacts = build_tool_registry_from_file_artifacts(
                registry_file=str(root_file),
                settings=settings,
            )

        self.assertEqual(tuple(sorted(artifacts["registry"])), ("provider_search",))
        self.assertEqual(
            artifacts["diagnostics"]["missing_registry_files"],
            (str(missing_file.resolve()),),
        )

    def test_build_tool_registry_from_file_artifacts_resolves_registry_source_relative_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_dir = Path(tmpdir) / "configs"
            root_dir.mkdir()
            root_file = root_dir / "root-manifest.json"
            child_file = root_dir / "child-source-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_sources": ["search_suite"],
                    }
                ),
                encoding="utf-8",
            )
            child_file.write_text(
                json.dumps(
                    {
                        "extra_tools": {
                            "provider_search": {
                                "template": "task_retrieve",
                                "label": "Provider Search",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "search_suite": {
                            "registry_file": "child-source-registry.json",
                        }
                    }
                )
            )

            artifacts = build_tool_registry_from_file_artifacts(
                registry_file=str(root_file),
                settings=settings,
            )

        self.assertIn("provider_search", artifacts["registry"])
        self.assertEqual(artifacts["diagnostics"]["missing_registry_sources"], ())
        self.assertEqual(artifacts["diagnostics"]["missing_registry_files"], ())

    def test_build_tool_registry_from_file_artifacts_resolves_registry_source_relative_named_provider_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_dir = Path(tmpdir) / "configs"
            root_dir.mkdir()
            root_file = root_dir / "root-manifest.json"
            child_file = root_dir / "child-source-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_sources": ["search_suite"],
                    }
                ),
                encoding="utf-8",
            )
            child_file.write_text(
                json.dumps(
                    {
                        "extra_tools": {
                            "provider_search": {
                                "template": "task_retrieve",
                                "label": "Provider Search",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_providers_json=json.dumps(
                    {
                        "search_provider": {
                            "registry_file": "child-source-registry.json",
                        }
                    }
                ),
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "search_suite": {
                            "provider": "search_provider",
                        }
                    }
                ),
            )

            artifacts = build_tool_registry_from_file_artifacts(
                registry_file=str(root_file),
                settings=settings,
            )

        self.assertIn("provider_search", artifacts["registry"])
        self.assertEqual(artifacts["diagnostics"]["missing_registry_sources"], ())
        self.assertEqual(artifacts["diagnostics"]["missing_registry_files"], ())

    def test_build_tool_registry_from_file_artifacts_reports_registry_source_relative_missing_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_dir = Path(tmpdir) / "configs"
            root_dir.mkdir()
            root_file = root_dir / "root-manifest.json"
            missing_file = root_dir / "missing-source-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_sources": ["missing_suite"],
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "missing_suite": {
                            "registry_file": "missing-source-registry.json",
                        }
                    }
                )
            )

            artifacts = build_tool_registry_from_file_artifacts(
                registry_file=str(root_file),
                settings=settings,
            )

        self.assertEqual(artifacts["registry"], {})
        self.assertEqual(
            artifacts["diagnostics"]["missing_registry_sources"],
            ("missing_suite",),
        )
        self.assertEqual(
            artifacts["diagnostics"]["missing_registry_files"],
            (str(missing_file.resolve()),),
        )

    def test_build_tool_registry_from_file_artifacts_reports_registry_source_relative_named_provider_missing_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_dir = Path(tmpdir) / "configs"
            root_dir.mkdir()
            root_file = root_dir / "root-manifest.json"
            missing_file = root_dir / "missing-provider-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_sources": ["missing_suite"],
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_providers_json=json.dumps(
                    {
                        "missing_provider": {
                            "registry_file": "missing-provider-registry.json",
                        }
                    }
                ),
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "missing_suite": {
                            "provider": "missing_provider",
                        }
                    }
                ),
            )

            artifacts = build_tool_registry_from_file_artifacts(
                registry_file=str(root_file),
                settings=settings,
            )

        self.assertEqual(artifacts["registry"], {})
        self.assertEqual(
            artifacts["diagnostics"]["missing_registry_sources"],
            ("missing_suite",),
        )
        self.assertEqual(
            artifacts["diagnostics"]["missing_registry_files"],
            (str(missing_file.resolve()),),
        )

    def test_build_tool_registry_from_file_artifacts_reports_registry_source_relative_loader_missing_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_dir = Path(tmpdir) / "configs"
            root_dir.mkdir()
            root_file = root_dir / "root-manifest.json"
            missing_file = root_dir / "missing-loader-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_sources": ["missing_suite"],
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_loaders_json=json.dumps(
                    {
                        "missing_loader": {
                            "registry_file": "missing-loader-registry.json",
                        }
                    }
                ),
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "missing_suite": {
                            "loader": "missing_loader",
                        }
                    }
                ),
            )

            artifacts = build_tool_registry_from_file_artifacts(
                registry_file=str(root_file),
                settings=settings,
            )

        self.assertEqual(artifacts["registry"], {})
        self.assertEqual(
            artifacts["diagnostics"]["missing_registry_sources"],
            ("missing_suite",),
        )
        self.assertEqual(
            artifacts["diagnostics"]["missing_registry_files"],
            (str(missing_file.resolve()),),
        )

    def test_build_tool_registry_from_file_artifacts_reports_registry_source_relative_loader_factory_missing_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_dir = Path(tmpdir) / "configs"
            root_dir.mkdir()
            root_file = root_dir / "root-manifest.json"
            missing_file = root_dir / "missing-loader-factory-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_sources": ["missing_suite"],
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_loader_factories_json=json.dumps(
                    {
                        "missing_loader_factory": {
                            "registry_file": "missing-loader-factory-registry.json",
                        }
                    }
                ),
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "missing_suite": {
                            "loader_factory": "missing_loader_factory",
                        }
                    }
                ),
            )

            artifacts = build_tool_registry_from_file_artifacts(
                registry_file=str(root_file),
                settings=settings,
            )

        self.assertEqual(artifacts["registry"], {})
        self.assertEqual(
            artifacts["diagnostics"]["missing_registry_sources"],
            ("missing_suite",),
        )
        self.assertEqual(
            artifacts["diagnostics"]["missing_registry_files"],
            (str(missing_file.resolve()),),
        )

    def test_build_tool_registry_from_file_artifacts_reports_registry_source_relative_provider_factory_missing_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_dir = Path(tmpdir) / "configs"
            root_dir.mkdir()
            root_file = root_dir / "root-manifest.json"
            missing_file = root_dir / "missing-provider-factory-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_sources": ["missing_suite"],
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_factories_json=json.dumps(
                    {
                        "missing_provider_factory": {
                            "registry_file": "missing-provider-factory-registry.json",
                        }
                    }
                ),
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "missing_suite": {
                            "provider_factory": "missing_provider_factory",
                        }
                    }
                ),
            )

            artifacts = build_tool_registry_from_file_artifacts(
                registry_file=str(root_file),
                settings=settings,
            )

        self.assertEqual(artifacts["registry"], {})
        self.assertEqual(
            artifacts["diagnostics"]["missing_registry_sources"],
            ("missing_suite",),
        )
        self.assertEqual(
            artifacts["diagnostics"]["missing_registry_files"],
            (str(missing_file.resolve()),),
        )

    def test_build_tool_registry_from_file_artifacts_reports_registry_source_relative_provider_loader_factory_missing_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_dir = Path(tmpdir) / "configs"
            root_dir.mkdir()
            root_file = root_dir / "root-manifest.json"
            missing_file = root_dir / "missing-loader-factory-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_sources": ["missing_suite"],
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_loader_factories_json=json.dumps(
                    {
                        "missing_loader_factory": {
                            "registry_file": "missing-loader-factory-registry.json",
                        }
                    }
                ),
                tool_registry_providers_json=json.dumps(
                    {
                        "missing_provider": {
                            "loader_factory": "missing_loader_factory",
                        }
                    }
                ),
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "missing_suite": {
                            "provider": "missing_provider",
                        }
                    }
                ),
            )

            artifacts = build_tool_registry_from_file_artifacts(
                registry_file=str(root_file),
                settings=settings,
            )

        self.assertEqual(artifacts["registry"], {})
        self.assertEqual(
            artifacts["diagnostics"]["missing_registry_sources"],
            ("missing_suite",),
        )
        self.assertEqual(
            artifacts["diagnostics"]["missing_registry_files"],
            (str(missing_file.resolve()),),
        )

    def test_build_tool_registry_from_file_artifacts_reports_registry_source_relative_provider_provider_factory_missing_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_dir = Path(tmpdir) / "configs"
            root_dir.mkdir()
            root_file = root_dir / "root-manifest.json"
            missing_file = root_dir / "missing-provider-factory-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_sources": ["missing_suite"],
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_factories_json=json.dumps(
                    {
                        "missing_provider_factory": {
                            "registry_file": "missing-provider-factory-registry.json",
                        }
                    }
                ),
                tool_registry_providers_json=json.dumps(
                    {
                        "missing_provider": {
                            "provider_factory": "missing_provider_factory",
                        }
                    }
                ),
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "missing_suite": {
                            "provider": "missing_provider",
                        }
                    }
                ),
            )

            artifacts = build_tool_registry_from_file_artifacts(
                registry_file=str(root_file),
                settings=settings,
            )

        self.assertEqual(artifacts["registry"], {})
        self.assertEqual(
            artifacts["diagnostics"]["missing_registry_sources"],
            ("missing_suite",),
        )
        self.assertEqual(
            artifacts["diagnostics"]["missing_registry_files"],
            (str(missing_file.resolve()),),
        )

    def test_build_tool_registry_from_file_artifacts_reports_registry_source_relative_source_chain_missing_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_dir = Path(tmpdir) / "configs"
            root_dir.mkdir()
            root_file = root_dir / "root-manifest.json"
            missing_file = root_dir / "missing-inner-source-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_sources": ["outer_suite"],
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "inner_suite": {
                            "registry_file": "missing-inner-source-registry.json",
                        },
                        "outer_suite": {
                            "provider": "inner_suite",
                        },
                    }
                )
            )

            artifacts = build_tool_registry_from_file_artifacts(
                registry_file=str(root_file),
                settings=settings,
            )

        self.assertEqual(artifacts["registry"], {})
        self.assertEqual(
            artifacts["diagnostics"]["missing_registry_sources"],
            ("outer_suite",),
        )
        self.assertEqual(
            artifacts["diagnostics"]["missing_registry_files"],
            (str(missing_file.resolve()),),
        )

    def test_build_tool_registry_from_file_artifacts_reports_registry_source_forward_source_chain_missing_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_dir = Path(tmpdir) / "configs"
            root_dir.mkdir()
            root_file = root_dir / "root-manifest.json"
            missing_file = root_dir / "missing-inner-source-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_sources": ["outer_suite"],
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "outer_suite": {
                            "provider": "inner_suite",
                        },
                        "inner_suite": {
                            "registry_file": "missing-inner-source-registry.json",
                        },
                    }
                )
            )

            artifacts = build_tool_registry_from_file_artifacts(
                registry_file=str(root_file),
                settings=settings,
            )

        self.assertEqual(artifacts["registry"], {})
        self.assertEqual(
            artifacts["diagnostics"]["missing_registry_sources"],
            ("outer_suite",),
        )
        self.assertEqual(
            artifacts["diagnostics"]["missing_registry_files"],
            (str(missing_file.resolve()),),
        )

    def test_build_tool_registry_from_file_artifacts_resolves_registry_source_relative_source_chain_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_dir = Path(tmpdir) / "configs"
            root_dir.mkdir()
            root_file = root_dir / "root-manifest.json"
            child_file = root_dir / "inner-source-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_sources": ["outer_suite"],
                    }
                ),
                encoding="utf-8",
            )
            child_file.write_text(
                json.dumps(
                    {
                        "extra_tools": {
                            "provider_search": {
                                "template": "task_retrieve",
                                "label": "Provider Search",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "inner_suite": {
                            "registry_file": "inner-source-registry.json",
                        },
                        "outer_suite": {
                            "provider": "inner_suite",
                        },
                    }
                )
            )

            artifacts = build_tool_registry_from_file_artifacts(
                registry_file=str(root_file),
                settings=settings,
            )

        self.assertIn("provider_search", artifacts["registry"])
        self.assertEqual(artifacts["diagnostics"]["missing_registry_sources"], ())
        self.assertEqual(artifacts["diagnostics"]["missing_registry_files"], ())

    def test_build_tool_registry_from_file_artifacts_resolves_registry_source_forward_source_chain_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_dir = Path(tmpdir) / "configs"
            root_dir.mkdir()
            root_file = root_dir / "root-manifest.json"
            child_file = root_dir / "inner-source-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_sources": ["outer_suite"],
                    }
                ),
                encoding="utf-8",
            )
            child_file.write_text(
                json.dumps(
                    {
                        "extra_tools": {
                            "provider_search": {
                                "template": "task_retrieve",
                                "label": "Provider Search",
                                "kind": "provider_retrieval",
                                "runtime_semantic_kind": "provider_search",
                                "execution": {
                                    "kind": "http_json",
                                    "url": "https://provider.example/search",
                                    "method": "POST",
                                    "query_params": {
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                        "q": "$query",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "documents_total": "$.total",
                                        "knowledge_base_id": "$.kb",
                                    },
                                },
                                "result_preview_keys": ["documents_total"],
                                "result_output_keys": [
                                    "documents_total",
                                    "knowledge_base_id",
                                ],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "outer_suite": {
                            "provider": "inner_suite",
                            "profile": "planning_only",
                        },
                        "inner_suite": {
                            "registry_file": "inner-source-registry.json",
                            "profile": "retrieval_only",
                        },
                    }
                )
            )

            artifacts = build_tool_registry_from_file_artifacts(
                registry_file=str(root_file),
                settings=settings,
            )
            registry = artifacts["registry"]
            provider = StaticToolRegistryProvider(registry=registry)
            urlopen_calls: list[object] = []

            class FakeHttpResponse:
                def read(self) -> bytes:
                    return b'{"data":{"total":11,"kb":"inner-kb"}}'

                def __enter__(self) -> "FakeHttpResponse":
                    return self

                def __exit__(self, exc_type, exc, tb) -> bool:
                    return False

            original_urlopen = getattr(tool_runtime_module, "urlopen", None)
            try:
                tool_runtime_module.urlopen = lambda request, timeout=0: (  # type: ignore[attr-defined]
                    urlopen_calls.append(request)
                    or FakeHttpResponse()
                )

                output = run_tool(
                    name="provider_search",
                    tool_input={"query": "forward child source"},
                    prompt="search forward child source",
                    user_id="user-1",
                    attempt=0,
                    registry_provider=provider,
                )
            finally:
                if original_urlopen is None:
                    delattr(tool_runtime_module, "urlopen")
                else:
                    tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(artifacts["diagnostics"]["missing_registry_sources"], ())
        self.assertIn("provider_search", registry)
        self.assertEqual(output["documents_total"], 11)
        self.assertEqual(output["knowledge_base_id"], "inner-kb")
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        parsed_query = parse_qs(urlparse(request.full_url).query)
        self.assertEqual(parsed_query["source"], ["inner_suite"])
        self.assertEqual(parsed_query["profile"], ["retrieval_only"])
        self.assertEqual(parsed_query["q"], ["forward child source"])

    def test_build_tool_registry_from_file_artifacts_skips_registry_source_self_cycle(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_sources": ["self_suite"],
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "self_suite": {
                            "registry_file": str(root_file),
                        }
                    }
                )
            )

            artifacts = build_tool_registry_from_file_artifacts(
                registry_file=str(root_file),
                settings=settings,
            )

        self.assertEqual(artifacts["registry"], {})
        self.assertEqual(
            artifacts["diagnostics"]["skipped_registry_sources"],
            ("self_suite",),
        )
        self.assertEqual(artifacts["diagnostics"]["missing_registry_sources"], ())

    def test_build_tool_registry_from_file_artifacts_skips_registry_source_relative_self_cycle(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_dir = Path(tmpdir) / "configs"
            root_dir.mkdir()
            root_file = root_dir / "root-manifest.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_sources": ["self_suite"],
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "self_suite": {
                            "registry_file": "root-manifest.json",
                        }
                    }
                )
            )

            artifacts = build_tool_registry_from_file_artifacts(
                registry_file=str(root_file),
                settings=settings,
            )

        self.assertEqual(artifacts["registry"], {})
        self.assertEqual(
            artifacts["diagnostics"]["skipped_registry_sources"],
            ("self_suite",),
        )
        self.assertEqual(artifacts["diagnostics"]["missing_registry_sources"], ())
        self.assertEqual(artifacts["diagnostics"]["missing_registry_files"], ())

    def test_build_tool_registry_from_file_artifacts_skips_registry_source_relative_named_provider_self_cycle(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_dir = Path(tmpdir) / "configs"
            root_dir.mkdir()
            root_file = root_dir / "root-manifest.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_sources": ["self_suite"],
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_providers_json=json.dumps(
                    {
                        "self_provider": {
                            "registry_file": "root-manifest.json",
                        }
                    }
                ),
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "self_suite": {
                            "provider": "self_provider",
                        }
                    }
                ),
            )

            artifacts = build_tool_registry_from_file_artifacts(
                registry_file=str(root_file),
                settings=settings,
            )

        self.assertEqual(artifacts["registry"], {})
        self.assertEqual(
            artifacts["diagnostics"]["skipped_registry_sources"],
            ("self_suite",),
        )
        self.assertEqual(artifacts["diagnostics"]["missing_registry_sources"], ())
        self.assertEqual(artifacts["diagnostics"]["missing_registry_files"], ())

    def test_build_tool_registry_from_file_artifacts_skips_registry_source_named_provider_self_cycle(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_sources": ["self_suite"],
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_providers_json=json.dumps(
                    {
                        "self_provider": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "self_suite": {
                            "provider": "self_provider",
                        }
                    }
                ),
            )

            artifacts = build_tool_registry_from_file_artifacts(
                registry_file=str(root_file),
                settings=settings,
            )

        self.assertEqual(artifacts["registry"], {})
        self.assertEqual(
            artifacts["diagnostics"]["skipped_registry_sources"],
            ("self_suite",),
        )
        self.assertEqual(artifacts["diagnostics"]["missing_registry_sources"], ())

    def test_build_tool_registry_from_file_artifacts_skips_registry_source_provider_loader_self_cycle(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_sources": ["self_suite"],
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_loaders_json=json.dumps(
                    {
                        "self_loader": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
                tool_registry_providers_json=json.dumps(
                    {
                        "self_provider": {
                            "loader": "self_loader",
                        }
                    }
                ),
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "self_suite": {
                            "provider": "self_provider",
                        }
                    }
                ),
            )

            artifacts = build_tool_registry_from_file_artifacts(
                registry_file=str(root_file),
                settings=settings,
            )

        self.assertEqual(artifacts["registry"], {})
        self.assertEqual(
            artifacts["diagnostics"]["skipped_registry_sources"],
            ("self_suite",),
        )
        self.assertEqual(artifacts["diagnostics"]["missing_registry_sources"], ())

    def test_build_tool_registry_from_file_artifacts_skips_registry_source_provider_loader_factory_self_cycle(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_sources": ["self_suite"],
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_loader_factories_json=json.dumps(
                    {
                        "self_loader_factory": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
                tool_registry_providers_json=json.dumps(
                    {
                        "self_provider": {
                            "loader_factory": "self_loader_factory",
                        }
                    }
                ),
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "self_suite": {
                            "provider": "self_provider",
                        }
                    }
                ),
            )

            artifacts = build_tool_registry_from_file_artifacts(
                registry_file=str(root_file),
                settings=settings,
            )

        self.assertEqual(artifacts["registry"], {})
        self.assertEqual(
            artifacts["diagnostics"]["skipped_registry_sources"],
            ("self_suite",),
        )
        self.assertEqual(artifacts["diagnostics"]["missing_registry_sources"], ())

    def test_build_tool_registry_from_file_artifacts_skips_registry_source_provider_factory_self_cycle(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_sources": ["self_suite"],
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_factories_json=json.dumps(
                    {
                        "self_provider_factory": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "self_suite": {
                            "provider_factory": "self_provider_factory",
                        }
                    }
                ),
            )

            artifacts = build_tool_registry_from_file_artifacts(
                registry_file=str(root_file),
                settings=settings,
            )

        self.assertEqual(artifacts["registry"], {})
        self.assertEqual(
            artifacts["diagnostics"]["skipped_registry_sources"],
            ("self_suite",),
        )
        self.assertEqual(artifacts["diagnostics"]["missing_registry_sources"], ())

    def test_build_tool_registry_from_file_artifacts_skips_registry_source_chain_self_cycle(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_sources": ["outer_suite"],
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "inner_suite": {
                            "registry_file": str(root_file),
                        },
                        "outer_suite": {
                            "provider": "inner_suite",
                        },
                    }
                )
            )

            artifacts = build_tool_registry_from_file_artifacts(
                registry_file=str(root_file),
                settings=settings,
            )

        self.assertEqual(artifacts["registry"], {})
        self.assertEqual(
            artifacts["diagnostics"]["skipped_registry_sources"],
            ("outer_suite",),
        )
        self.assertEqual(artifacts["diagnostics"]["missing_registry_sources"], ())

    def test_build_tool_registry_from_file_artifacts_skips_registry_source_provider_cycle(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_sources": ["outer_suite"],
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "outer_suite": {
                            "provider": "inner_suite",
                        },
                        "inner_suite": {
                            "provider": "outer_suite",
                        },
                    }
                )
            )

            artifacts = build_tool_registry_from_file_artifacts(
                registry_file=str(root_file),
                settings=settings,
            )

        self.assertEqual(artifacts["registry"], {})
        self.assertEqual(
            artifacts["diagnostics"]["skipped_registry_sources"],
            ("inner_suite", "outer_suite"),
        )
        self.assertEqual(artifacts["diagnostics"]["missing_registry_sources"], ())

    def test_build_tool_registry_providers_from_settings_accepts_registry_file_with_registry_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_sources": ["planning_suite"],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "planning_suite": {
                            "provider_factory": "planning_only",
                            "overrides": {
                                "calc_eval": {
                                    "enabled": True,
                                    "label": "Planning Calculator",
                                }
                            },
                        }
                    }
                ),
                tool_registry_providers_json=json.dumps(
                    {
                        "file_provider": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )

            providers = build_tool_registry_providers_from_settings(settings=settings)
            registry = providers["file_provider"].load_tool_registry()

        self.assertEqual(tuple(sorted(providers)), ("file_provider",))
        self.assertEqual(
            tuple(sorted(registry)),
            ("calc_eval", "calc_eval_fast", "task_plan"),
        )
        self.assertEqual(registry["calc_eval"].label, "Planning Calculator")

    def test_build_tool_registry_from_file_ignores_duplicate_registry_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_sources": [
                            "planning_suite",
                            "planning_suite",
                        ],
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "planning_suite": {
                            "provider_factory": "planning_only",
                            "overrides": {
                                "calc_eval": {
                                    "enabled": True,
                                    "label": "Planning Calculator",
                                }
                            },
                        }
                    }
                )
            )

            registry = build_tool_registry_from_file(
                registry_file=str(root_file),
                settings=settings,
            )

        self.assertEqual(
            tuple(sorted(registry)),
            ("calc_eval", "task_plan"),
        )
        self.assertEqual(registry["calc_eval"].label, "Planning Calculator")

    def test_build_tool_registry_from_file_ignores_duplicate_registry_files_and_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_file = Path(tmpdir) / "base-registry.json"
            base_file.write_text(
                json.dumps(
                    {
                        "calc_eval_fast": {
                            "template": "calc_eval",
                            "label": "Fast Calculator",
                        }
                    }
                ),
                encoding="utf-8",
            )
            registry_dir = Path(tmpdir) / "registry-parts"
            registry_dir.mkdir()
            (registry_dir / "10-overlay.json").write_text(
                json.dumps(
                    {
                        "profile": "planning_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Planning Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            root_file = Path(tmpdir) / "root-manifest.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(base_file), str(base_file)],
                        "registry_dirs": [str(registry_dir), str(registry_dir)],
                    }
                ),
                encoding="utf-8",
            )

            registry = build_tool_registry_from_file(registry_file=str(root_file))

        self.assertEqual(
            tuple(sorted(registry)),
            ("calc_eval", "calc_eval_fast", "task_plan"),
        )
        self.assertEqual(registry["calc_eval"].label, "Planning Calculator")

    def test_build_tool_registry_from_file_ignores_registry_file_self_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_file = Path(tmpdir) / "base-registry.json"
            base_file.write_text(
                json.dumps(
                    {
                        "calc_eval_fast": {
                            "template": "calc_eval",
                            "label": "Fast Calculator",
                        }
                    }
                ),
                encoding="utf-8",
            )
            root_file = Path(tmpdir) / "root-manifest.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [
                            str(root_file),
                            str(base_file),
                        ],
                    }
                ),
                encoding="utf-8",
            )

            registry = build_tool_registry_from_file(registry_file=str(root_file))

        self.assertEqual(tuple(sorted(registry)), ("calc_eval_fast",))
