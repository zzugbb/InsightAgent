from __future__ import annotations

from .context import *


class RegistryFileDiagnosticsMixin:
    def test_build_tool_registry_extra_tools_from_settings_ignores_unknown_template_and_existing_name(self) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "calc_eval": {
                        "template": "calc_eval",
                        "label": "Should Ignore Existing Name",
                    },
                    "custom_unknown": {
                        "template": "missing_tool",
                        "label": "Should Ignore Unknown Template",
                    },
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        self.assertEqual(extra_tools, {})

    def test_build_tool_registry_provider_sources_from_settings_groups_named_sources(self) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_sources_json=json.dumps(
                {
                    "analytics_suite": {
                        "calc_eval_fast": {
                            "template": "calc_eval",
                            "label": "Fast Calculator",
                            "default_timeout_ms": 1_500,
                        }
                    },
                    "retrieval_suite": {
                        "mock_retrieve_hot": {
                            "template": "mock_retrieve",
                            "label": "Hot Retrieval",
                        }
                    },
                }
            )
        )

        sources = build_tool_registry_provider_sources_from_settings(settings=settings)

        self.assertEqual(tuple(sorted(sources)), ("analytics_suite", "retrieval_suite"))
        self.assertEqual(
            tuple(sorted(sources["analytics_suite"].load_tool_registry())),
            ("calc_eval_fast",),
        )
        self.assertEqual(
            sources["analytics_suite"].load_tool_registry()["calc_eval_fast"].label,
            "Fast Calculator",
        )

    def test_build_tool_registry_provider_sources_from_settings_supports_adapter_shape(self) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_sources_json=json.dumps(
                {
                    "planning_suite": {
                        "provider": "default",
                        "profile": "planning_only",
                        "disabled_tool_names": ["mock_plan"],
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Planning Calculator",
                            }
                        },
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                }
            )
        )

        sources = build_tool_registry_provider_sources_from_settings(settings=settings)

        self.assertEqual(tuple(sorted(sources)), ("planning_suite",))
        self.assertEqual(
            get_registered_tool_names(registry_provider=sources["planning_suite"]),
            ("calc_eval", "calc_eval_fast"),
        )
        self.assertEqual(
            sources["planning_suite"].load_tool_registry()["calc_eval"].label,
            "Planning Calculator",
        )

    def test_build_tool_registry_provider_sources_from_settings_accepts_json_string_wrappers(self) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_sources_json=UserString(
                json.dumps(
                    {
                        "planning_suite": {
                            "provider": "default",
                            "profile": "planning_only",
                            "disabled_tool_names": ["mock_plan"],
                            "extra_tools": {
                                "calc_eval_fast": {
                                    "template": "calc_eval",
                                    "label": "Fast Calculator",
                                }
                            },
                        }
                    }
                )
            )
        )

        sources = build_tool_registry_provider_sources_from_settings(settings=settings)

        self.assertEqual(tuple(sorted(sources)), ("planning_suite",))
        self.assertEqual(
            get_registered_tool_names(registry_provider=sources["planning_suite"]),
            ("calc_eval_fast",),
        )

    def test_build_tool_registry_provider_sources_from_settings_ignores_bad_shapes(self) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_sources_json=json.dumps(
                {
                    "broken": "bad-shape",
                    "also_broken": {
                        "calc_eval": {
                            "template": "missing_template",
                        }
                    },
                }
            )
        )

        sources = build_tool_registry_provider_sources_from_settings(settings=settings)

        self.assertEqual(sources, {})

    def test_build_tool_registry_provider_sources_from_settings_ignores_unknown_provider_name(self) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_sources_json=json.dumps(
                {
                    "broken_suite": {
                        "provider": "missing",
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                            }
                        },
                    }
                }
            )
        )

        sources = build_tool_registry_provider_sources_from_settings(settings=settings)

        self.assertEqual(sources, {})

    def test_build_tool_registry_provider_adapter_accepts_tuple_result_preview_keys_in_overrides(
        self,
    ) -> None:
        provider = tool_runtime_module.build_tool_registry_provider_adapter(
            spec={
                "provider": "default",
                "overrides": {
                    "task_retrieve": {
                        "result_preview_keys": (
                            "documents_total",
                        ),
                    }
                },
            }
        )

        self.assertIsNotNone(provider)
        assert provider is not None
        self.assertEqual(
            provider.load_tool_registry()["task_retrieve"].result_preview_keys,
            ("documents_total",),
        )

    def test_build_tool_registry_provider_adapter_accepts_tuple_result_output_keys_in_overrides(
        self,
    ) -> None:
        provider = tool_runtime_module.build_tool_registry_provider_adapter(
            spec={
                "provider": "default",
                "overrides": {
                    "task_retrieve": {
                        "result_output_keys": (
                            "documents_total",
                            "request_id",
                        ),
                    }
                },
            }
        )

        self.assertIsNotNone(provider)
        assert provider is not None
        self.assertEqual(
            provider.load_tool_registry()["task_retrieve"].result_output_keys,
            ("documents_total", "request_id"),
        )

    def test_build_tool_registry_provider_adapter_registry_file_uses_source_template_context(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "source-registry.json"
            registry_file.write_text(
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
                                    "query_params": {
                                        "source": "$tool_registry_provider_source",
                                        "q": "$query",
                                    },
                                    "result_fields": {
                                        "documents_total": "$.meta.total",
                                    },
                                },
                                "result_preview_keys": ["documents_total"],
                                "result_output_keys": ["documents_total"],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            provider = tool_runtime_module.build_tool_registry_provider_adapter(
                spec={"registry_file": str(registry_file)},
                settings=SimpleNamespace(
                    tool_registry_provider_source="global_selected",
                ),
                provider_source_name="file_source",
            )
            self.assertIsNotNone(provider)
            assert provider is not None
            urlopen_calls: list[object] = []

            class FakeHttpResponse:
                def read(self) -> bytes:
                    return b'{"meta":{"total":8}}'

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
                    tool_input={"query": "cash flow"},
                    prompt="search cash flow",
                    user_id="user-1",
                    attempt=0,
                    registry_provider=provider,
                )
            finally:
                if original_urlopen is None:
                    delattr(tool_runtime_module, "urlopen")
                else:
                    tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(output["documents_total"], 8)
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        self.assertEqual(
            request.full_url,
            "https://provider.example/search?source=file_source&q=cash+flow",
        )

    def test_build_tool_registry_provider_adapter_plain_registry_file_uses_source_template_context(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "plain-source-registry.json"
            registry_file.write_text(
                json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "runtime_semantic_kind": "provider_search",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/search",
                                "query_params": {
                                    "source": "$tool_registry_provider_source",
                                    "q": "$query",
                                },
                                "result_fields": {
                                    "documents_total": "$.meta.total",
                                },
                            },
                            "result_preview_keys": ["documents_total"],
                            "result_output_keys": ["documents_total"],
                        }
                    }
                ),
                encoding="utf-8",
            )
            provider = tool_runtime_module.build_tool_registry_provider_adapter(
                spec={"registry_file": str(registry_file)},
                settings=SimpleNamespace(
                    tool_registry_provider_source="global_selected",
                ),
                provider_source_name="file_source",
            )
            self.assertIsNotNone(provider)
            assert provider is not None
            urlopen_calls: list[object] = []

            class FakeHttpResponse:
                def read(self) -> bytes:
                    return b'{"meta":{"total":13}}'

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
                    tool_input={"query": "plain cash flow"},
                    prompt="search plain cash flow",
                    user_id="user-1",
                    attempt=0,
                    registry_provider=provider,
                )
            finally:
                if original_urlopen is None:
                    delattr(tool_runtime_module, "urlopen")
                else:
                    tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(output["documents_total"], 13)
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        self.assertEqual(
            request.full_url,
            "https://provider.example/search?source=file_source&q=plain+cash+flow",
        )

    def test_build_tool_registry_provider_source_provider_factory_registry_file_uses_source_template_context(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "factory-source-registry.json"
            registry_file.write_text(
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
                                    "query_params": {
                                        "source": "$tool_registry_provider_source",
                                        "q": "$query",
                                    },
                                    "result_fields": {
                                        "documents_total": "$.meta.total",
                                    },
                                },
                                "result_preview_keys": ["documents_total"],
                                "result_output_keys": ["documents_total"],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="global_selected",
                tool_registry_provider_factories_json=json.dumps(
                    {
                        "file_factory": {
                            "registry_file": str(registry_file),
                        }
                    }
                ),
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "provider_factory": "file_factory",
                        }
                    }
                ),
            )
            sources = build_tool_registry_provider_sources_from_settings(
                settings=settings,
            )
            provider = sources["file_source"]
            urlopen_calls: list[object] = []

            class FakeHttpResponse:
                def read(self) -> bytes:
                    return b'{"meta":{"total":9}}'

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
                    tool_input={"query": "factory cash flow"},
                    prompt="search factory cash flow",
                    user_id="user-1",
                    attempt=0,
                    registry_provider=provider,
                )
            finally:
                if original_urlopen is None:
                    delattr(tool_runtime_module, "urlopen")
                else:
                    tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(output["documents_total"], 9)
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        self.assertEqual(
            request.full_url,
            "https://provider.example/search?source=file_source&q=factory+cash+flow",
        )

    def test_build_tool_registry_provider_source_loader_factory_registry_file_uses_source_template_context(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "loader-factory-source-registry.json"
            registry_file.write_text(
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
                                    "query_params": {
                                        "source": "$tool_registry_provider_source",
                                        "q": "$query",
                                    },
                                    "result_fields": {
                                        "documents_total": "$.meta.total",
                                    },
                                },
                                "result_preview_keys": ["documents_total"],
                                "result_output_keys": ["documents_total"],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="global_selected",
                tool_registry_loader_factories_json=json.dumps(
                    {
                        "file_factory": {
                            "registry_file": str(registry_file),
                        }
                    }
                ),
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "loader_factory": "file_factory",
                        }
                    }
                ),
            )
            sources = build_tool_registry_provider_sources_from_settings(
                settings=settings,
            )
            provider = sources["file_source"]
            urlopen_calls: list[object] = []

            class FakeHttpResponse:
                def read(self) -> bytes:
                    return b'{"meta":{"total":10}}'

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
                    tool_input={"query": "loader factory cash flow"},
                    prompt="search loader factory cash flow",
                    user_id="user-1",
                    attempt=0,
                    registry_provider=provider,
                )
            finally:
                if original_urlopen is None:
                    delattr(tool_runtime_module, "urlopen")
                else:
                    tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(output["documents_total"], 10)
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        self.assertEqual(
            request.full_url,
            "https://provider.example/search?source=file_source&q=loader+factory+cash+flow",
        )

    def test_build_tool_registry_provider_source_named_provider_registry_file_uses_source_template_context(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "named-provider-source-registry.json"
            registry_file.write_text(
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
                                    "query_params": {
                                        "source": "$tool_registry_provider_source",
                                        "q": "$query",
                                    },
                                    "result_fields": {
                                        "documents_total": "$.meta.total",
                                    },
                                },
                                "result_preview_keys": ["documents_total"],
                                "result_output_keys": ["documents_total"],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="global_selected",
                tool_registry_providers_json=json.dumps(
                    {
                        "file_provider": {
                            "registry_file": str(registry_file),
                        }
                    }
                ),
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "provider": "file_provider",
                        }
                    }
                ),
            )
            sources = build_tool_registry_provider_sources_from_settings(
                settings=settings,
            )
            provider = sources["file_source"]
            urlopen_calls: list[object] = []

            class FakeHttpResponse:
                def read(self) -> bytes:
                    return b'{"meta":{"total":11}}'

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
                    tool_input={"query": "named provider cash flow"},
                    prompt="search named provider cash flow",
                    user_id="user-1",
                    attempt=0,
                    registry_provider=provider,
                )
            finally:
                if original_urlopen is None:
                    delattr(tool_runtime_module, "urlopen")
                else:
                    tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(output["documents_total"], 11)
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        self.assertEqual(
            request.full_url,
            "https://provider.example/search?source=file_source&q=named+provider+cash+flow",
        )

    def test_build_tool_registry_provider_source_named_loader_registry_file_uses_source_template_context(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "named-loader-source-registry.json"
            registry_file.write_text(
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
                                    "query_params": {
                                        "source": "$tool_registry_provider_source",
                                        "q": "$query",
                                    },
                                    "result_fields": {
                                        "documents_total": "$.meta.total",
                                    },
                                },
                                "result_preview_keys": ["documents_total"],
                                "result_output_keys": ["documents_total"],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="global_selected",
                tool_registry_loaders_json=json.dumps(
                    {
                        "file_loader": {
                            "registry_file": str(registry_file),
                        }
                    }
                ),
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "loader": "file_loader",
                        }
                    }
                ),
            )
            sources = build_tool_registry_provider_sources_from_settings(
                settings=settings,
            )
            provider = sources["file_source"]
            urlopen_calls: list[object] = []

            class FakeHttpResponse:
                def read(self) -> bytes:
                    return b'{"meta":{"total":12}}'

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
                    tool_input={"query": "named loader cash flow"},
                    prompt="search named loader cash flow",
                    user_id="user-1",
                    attempt=0,
                    registry_provider=provider,
                )
            finally:
                if original_urlopen is None:
                    delattr(tool_runtime_module, "urlopen")
                else:
                    tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(output["documents_total"], 12)
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        self.assertEqual(
            request.full_url,
            "https://provider.example/search?source=file_source&q=named+loader+cash+flow",
        )

    def test_build_tool_registry_loader_adapter_accepts_tuple_disabled_tool_names(
        self,
    ) -> None:
        loader = tool_runtime_module.build_tool_registry_loader_adapter(
            spec={
                "loader": "default",
                "disabled_tool_names": ("mock_plan",),
            }
        )

        self.assertIsNotNone(loader)
        assert loader is not None
        self.assertEqual(
            tuple(sorted(loader().keys())),
            ("calc_eval", "task_retrieve"),
        )

    def test_build_tool_registry_loader_adapter_accepts_mapping_wrappers(
        self,
    ) -> None:
        loader = tool_runtime_module.build_tool_registry_loader_adapter(
            spec=UserDict(
                {
                    UserString("loader"): UserString("default"),
                    UserString("profile"): UserString("planning_only"),
                    UserString("disabled_tool_names"): UserList(
                        [UserString("mock_plan")]
                    ),
                    UserString("extra_tools"): UserDict(
                        {
                            UserString("calc_eval_fast"): UserDict(
                                {
                                    UserString("template"): UserString("calc_eval"),
                                    UserString("label"): UserString("Fast Calculator"),
                                }
                            )
                        }
                    ),
                }
            )
        )

        self.assertIsNotNone(loader)
        assert loader is not None
        registry = loader()
        self.assertEqual(tuple(sorted(registry)), ("calc_eval_fast",))
        self.assertEqual(registry["calc_eval_fast"].label, "Fast Calculator")

    def test_build_tool_registry_provider_adapter_accepts_tuple_disabled_tool_names(
        self,
    ) -> None:
        provider = tool_runtime_module.build_tool_registry_provider_adapter(
            spec={
                "provider": "default",
                "disabled_tool_names": ("mock_plan",),
            }
        )

        self.assertIsNotNone(provider)
        assert provider is not None
        self.assertEqual(
            get_registered_tool_names(registry_provider=provider),
            ("calc_eval", "task_retrieve"),
        )

    def test_build_tool_registry_providers_from_settings_supports_loader_adapter_shape(self) -> None:
        settings = SimpleNamespace(
            tool_registry_providers_json=json.dumps(
                {
                    "planning_provider": {
                        "loader": "default",
                        "profile": "planning_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Planning Calculator",
                            }
                        },
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                }
            )
        )

        providers = build_tool_registry_providers_from_settings(settings=settings)

        self.assertEqual(tuple(sorted(providers)), ("planning_provider",))
        self.assertEqual(
            get_registered_tool_names(registry_provider=providers["planning_provider"]),
            ("calc_eval", "calc_eval_fast", "task_plan"),
        )
        self.assertEqual(
            providers["planning_provider"].load_tool_registry()["calc_eval"].label,
            "Planning Calculator",
        )

    def test_build_tool_registry_loaders_from_settings_supports_adapter_shape(self) -> None:
        settings = SimpleNamespace(
            tool_registry_loaders_json=json.dumps(
                {
                    "planning_loader": {
                        "loader": "default",
                        "profile": "planning_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Planning Calculator",
                            }
                        },
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                }
            )
        )

        loaders = build_tool_registry_loaders_from_settings(settings=settings)
        planning_registry = loaders["planning_loader"]()

        self.assertEqual(tuple(sorted(loaders)), ("planning_loader",))
        self.assertEqual(
            tuple(sorted(planning_registry)),
            ("calc_eval", "calc_eval_fast", "task_plan"),
        )
        self.assertEqual(planning_registry["calc_eval"].label, "Planning Calculator")

    def test_build_tool_registry_loaders_from_settings_accepts_forward_named_loader_reference(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_loaders_json=json.dumps(
                {
                    "outer_loader": {
                        "loader": "inner_loader",
                        "disabled_tool_names": ["mock_plan"],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    },
                    "inner_loader": {
                        "loader": "default",
                        "profile": "planning_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Planning Calculator",
                            }
                        },
                    },
                }
            )
        )

        loaders = build_tool_registry_loaders_from_settings(settings=settings)
        outer_registry = loaders["outer_loader"]()

        self.assertEqual(tuple(sorted(loaders)), ("inner_loader", "outer_loader"))
        self.assertEqual(tuple(sorted(outer_registry)), ("calc_eval", "calc_eval_fast"))
        self.assertEqual(outer_registry["calc_eval"].label, "Planning Calculator")

    def test_build_tool_registry_loaders_from_settings_supports_loader_factory_shape(self) -> None:
        settings = SimpleNamespace(
            tool_registry_loaders_json=json.dumps(
                {
                    "planning_loader": {
                        "loader_factory": "planning_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Planning Calculator",
                            }
                        },
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                }
            )
        )

        loaders = build_tool_registry_loaders_from_settings(settings=settings)
        planning_registry = loaders["planning_loader"]()

        self.assertEqual(tuple(sorted(loaders)), ("planning_loader",))
        self.assertEqual(
            tuple(sorted(planning_registry)),
            ("calc_eval", "calc_eval_fast", "task_plan"),
        )
        self.assertEqual(planning_registry["calc_eval"].label, "Planning Calculator")

    def test_build_tool_registry_loaders_from_settings_reuses_shared_profile_name_helper(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_loaders_json=json.dumps(
                {
                    "planning_loader": {
                        "profile": " Planning_Only ",
                    }
                }
            )
        )
        original_get_tool_registry_profile_name_from_settings = (
            tool_runtime_module.get_tool_registry_profile_name_from_settings
        )
        captured: list[object] = []
        try:
            def fake_get_tool_registry_profile_name_from_settings(*, settings=None):
                captured.append(getattr(settings, "tool_registry_profile", None))
                if getattr(settings, "tool_registry_profile", None) == " Planning_Only ":
                    return "calculator_only"
                return original_get_tool_registry_profile_name_from_settings(
                    settings=settings
                )

            tool_runtime_module.get_tool_registry_profile_name_from_settings = (
                fake_get_tool_registry_profile_name_from_settings
            )
            loaders = build_tool_registry_loaders_from_settings(settings=settings)
        finally:
            tool_runtime_module.get_tool_registry_profile_name_from_settings = (
                original_get_tool_registry_profile_name_from_settings
            )

        self.assertEqual(tuple(sorted(loaders)), ("planning_loader",))
        self.assertIn(" Planning_Only ", captured)
        self.assertEqual(
            tuple(sorted(loaders["planning_loader"]())),
            ("calc_eval",),
        )

    def test_build_tool_registry_loaders_from_settings_reuses_shared_profile_name_helper_for_factory_hint(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_loaders_json=json.dumps(
                {
                    "planning_loader": {
                        "loader_factory": "custom_factory",
                    }
                }
            )
        )
        original_get_tool_registry_profile_name_from_settings = (
            tool_runtime_module.get_tool_registry_profile_name_from_settings
        )
        original_build_tool_registry_loader_factories_from_settings = (
            tool_runtime_module.build_tool_registry_loader_factories_from_settings
        )
        captured: list[object] = []
        try:
            def fake_get_tool_registry_profile_name_from_settings(*, settings=None):
                captured.append(getattr(settings, "tool_registry_profile", None))
                if getattr(settings, "tool_registry_profile", None) == " Planning_Only ":
                    return "calculator_only"
                return original_get_tool_registry_profile_name_from_settings(
                    settings=settings
                )

            def fake_build_tool_registry_loader_factories_from_settings(*, settings=None):
                def factory(_settings=None):
                    return tool_runtime_module.get_default_tool_registry

                setattr(factory, "_tool_registry_profile_name", " Planning_Only ")
                return {"custom_factory": factory}

            tool_runtime_module.get_tool_registry_profile_name_from_settings = (
                fake_get_tool_registry_profile_name_from_settings
            )
            tool_runtime_module.build_tool_registry_loader_factories_from_settings = (
                fake_build_tool_registry_loader_factories_from_settings
            )
            loaders = build_tool_registry_loaders_from_settings(settings=settings)
        finally:
            tool_runtime_module.get_tool_registry_profile_name_from_settings = (
                original_get_tool_registry_profile_name_from_settings
            )
            tool_runtime_module.build_tool_registry_loader_factories_from_settings = (
                original_build_tool_registry_loader_factories_from_settings
            )

        self.assertEqual(tuple(sorted(loaders)), ("planning_loader",))
        self.assertIn(" Planning_Only ", captured)
        self.assertEqual(
            tuple(sorted(loaders["planning_loader"]())),
            ("calc_eval",),
        )

    def test_build_tool_registry_loader_factories_from_settings_supports_named_factory_alias(self) -> None:
        settings = SimpleNamespace(
            tool_registry_loader_factories_json=json.dumps(
                {
                    "planning_factory": {
                        "factory": "planning_only",
                    }
                }
            )
        )

        factories = build_tool_registry_loader_factories_from_settings(settings=settings)
        planning_registry = factories["planning_factory"](settings)()

        self.assertEqual(tuple(sorted(factories)), ("planning_factory",))
        self.assertEqual(
            tuple(sorted(planning_registry)),
            ("task_plan",),
        )

    def test_build_tool_registry_loader_factories_from_settings_reuse_shared_reference_normalizer_for_factory_key(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_loader_factories_json=json.dumps(
                {
                    " Planning_Factory ": {
                        "factory": "planning_only",
                    }
                }
            )
        )
        original_normalize_named_tool_registry_component_name = getattr(
            tool_runtime_module,
            "_normalize_named_tool_registry_component_name",
        )
        captured: list[object] = []
        try:
            def fake_normalize_named_tool_registry_component_name(
                name: object | None,
            ) -> str | None:
                captured.append(name)
                if name == " Planning_Factory ":
                    return "planning_factory_shadow"
                if not isinstance(name, str):
                    return None
                normalized = name.strip().lower()
                return normalized or None

            tool_runtime_module._normalize_named_tool_registry_component_name = (
                fake_normalize_named_tool_registry_component_name
            )
            factories = build_tool_registry_loader_factories_from_settings(settings=settings)
        finally:
            tool_runtime_module._normalize_named_tool_registry_component_name = (
                original_normalize_named_tool_registry_component_name
            )

        self.assertIn(" Planning_Factory ", captured)
        self.assertEqual(tuple(sorted(factories)), ("planning_factory_shadow",))
        self.assertEqual(
            tuple(sorted(factories["planning_factory_shadow"](settings)())),
            ("task_plan",),
        )

    def test_build_tool_registry_provider_factories_from_settings_supports_named_factory_alias(self) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_factories_json=json.dumps(
                {
                    "planning_factory": {
                        "factory": "planning_only",
                    }
                }
            )
        )

        factories = build_tool_registry_provider_factories_from_settings(settings=settings)
        planning_registry = factories["planning_factory"](settings).load_tool_registry()

        self.assertEqual(tuple(sorted(factories)), ("planning_factory",))
        self.assertEqual(
            tuple(sorted(planning_registry)),
            ("task_plan",),
        )

    def test_build_tool_registry_loader_factories_from_settings_accepts_forward_named_factory_reference(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "tool-registry.json"
            registry_file.write_text(
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
            settings = SimpleNamespace(
                tool_registry_loader_factories_json=json.dumps(
                    {
                        "outer_factory": {
                            "factory": "inner_factory",
                        },
                        "inner_factory": {
                            "registry_file": str(registry_file),
                        },
                    }
                )
            )

            factories = build_tool_registry_loader_factories_from_settings(
                settings=settings
            )
            file_registry = factories["outer_factory"](settings)()

        self.assertEqual(tuple(sorted(factories)), ("inner_factory", "outer_factory"))
        self.assertEqual(tuple(sorted(file_registry)), ("calc_eval_fast",))
        self.assertEqual(file_registry["calc_eval_fast"].label, "Fast Calculator")

    def test_build_tool_registry_provider_factories_from_settings_accepts_forward_named_factory_reference(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "tool-registry.json"
            registry_file.write_text(
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
            settings = SimpleNamespace(
                tool_registry_provider_factories_json=json.dumps(
                    {
                        "outer_factory": {
                            "factory": "inner_factory",
                        },
                        "inner_factory": {
                            "registry_file": str(registry_file),
                        },
                    }
                )
            )

            factories = build_tool_registry_provider_factories_from_settings(
                settings=settings
            )
            file_registry = factories["outer_factory"](settings).load_tool_registry()

        self.assertEqual(tuple(sorted(factories)), ("inner_factory", "outer_factory"))
        self.assertEqual(tuple(sorted(file_registry)), ("calc_eval_fast",))
        self.assertEqual(file_registry["calc_eval_fast"].label, "Fast Calculator")

    def test_build_tool_registry_loader_factories_from_settings_supports_registry_file_factory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "tool-registry.json"
            registry_file.write_text(
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
            settings = SimpleNamespace(
                tool_registry_loader_factories_json=json.dumps(
                    {
                        "file_factory": {
                            "registry_file": str(registry_file),
                        }
                    }
                )
            )

            factories = build_tool_registry_loader_factories_from_settings(settings=settings)
            file_registry = factories["file_factory"](settings)()

        self.assertEqual(tuple(sorted(factories)), ("file_factory",))
        self.assertEqual(tuple(sorted(file_registry)), ("calc_eval_fast",))
        self.assertEqual(file_registry["calc_eval_fast"].label, "Fast Calculator")

    def test_build_tool_registry_provider_factories_from_settings_supports_registry_file_factory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "tool-registry.json"
            registry_file.write_text(
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
            settings = SimpleNamespace(
                tool_registry_provider_factories_json=json.dumps(
                    {
                        "file_factory": {
                            "registry_file": str(registry_file),
                        }
                    }
                )
            )

            factories = build_tool_registry_provider_factories_from_settings(settings=settings)
            file_registry = factories["file_factory"](settings).load_tool_registry()

        self.assertEqual(tuple(sorted(factories)), ("file_factory",))
        self.assertEqual(tuple(sorted(file_registry)), ("calc_eval_fast",))
        self.assertEqual(file_registry["calc_eval_fast"].label, "Fast Calculator")

    def test_build_tool_registry_loader_from_file_supports_manifest_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "tool-registry-manifest.json"
            registry_file.write_text(
                json.dumps(
                    {
                        "profile": "planning_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Planning Calculator",
                            }
                        },
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

            loader = build_tool_registry_loader_from_file(registry_file=str(registry_file))
            self.assertIsNotNone(loader)
            registry = loader()

        self.assertEqual(
            tuple(sorted(registry)),
            ("calc_eval", "calc_eval_fast", "task_plan"),
        )
        self.assertEqual(registry["calc_eval"].label, "Planning Calculator")

    def test_build_tool_registry_loaders_from_settings_accepts_json_string_wrappers(self) -> None:
        settings = SimpleNamespace(
            tool_registry_loaders_json=UserString(
                json.dumps(
                    {
                        "planning_loader": {
                            "loader": "default",
                            "profile": "planning_only",
                            "disabled_tool_names": ["mock_plan"],
                            "extra_tools": {
                                "calc_eval_fast": {
                                    "template": "calc_eval",
                                    "label": "Fast Calculator",
                                }
                            },
                        }
                    }
                )
            )
        )

        loaders = build_tool_registry_loaders_from_settings(settings=settings)
        registry = loaders["planning_loader"]()

        self.assertEqual(tuple(sorted(loaders)), ("planning_loader",))
        self.assertEqual(tuple(sorted(registry)), ("calc_eval_fast",))

    def test_build_tool_registry_provider_from_file_supports_manifest_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "tool-registry-manifest.json"
            registry_file.write_text(
                json.dumps(
                    {
                        "profile": "retrieval_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Retrieval Calculator",
                            }
                        },
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

            provider = build_tool_registry_provider_from_file(registry_file=str(registry_file))
            self.assertIsNotNone(provider)
            registry = provider.load_tool_registry()

        self.assertEqual(
            tuple(sorted(registry)),
            ("calc_eval", "calc_eval_fast", "task_retrieve"),
        )
        self.assertEqual(registry["calc_eval"].label, "Retrieval Calculator")

    def test_build_tool_registry_from_file_supports_registry_files_composition(self) -> None:
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
            overlay_file = Path(tmpdir) / "overlay-manifest.json"
            overlay_file.write_text(
                json.dumps(
                    {
                        "profile": "planning_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Planning Calculator",
                            }
                        },
                        "extra_tools": {
                            "mock_plan_brief": {
                                "template": "mock_plan",
                                "label": "Brief Planner",
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
                        "registry_files": [
                            str(base_file),
                            str(overlay_file),
                        ]
                    }
                ),
                encoding="utf-8",
            )

            registry = build_tool_registry_from_file(registry_file=str(root_file))

        self.assertEqual(
            tuple(sorted(registry)),
            ("calc_eval", "calc_eval_fast", "mock_plan_brief", "task_plan"),
        )
        self.assertEqual(registry["calc_eval"].label, "Planning Calculator")

    def test_build_tool_registry_from_file_resolves_relative_registry_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fixtures_dir = Path(tmpdir) / "fixtures"
            fixtures_dir.mkdir()
            nested_dir = fixtures_dir / "nested"
            nested_dir.mkdir()

            base_file = fixtures_dir / "base-registry.json"
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
            overlay_file = fixtures_dir / "overlay-manifest.json"
            overlay_file.write_text(
                json.dumps(
                    {
                        "profile": "retrieval_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Retrieval Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            root_file = nested_dir / "root-manifest.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [
                            "../base-registry.json",
                            "../overlay-manifest.json",
                        ]
                    }
                ),
                encoding="utf-8",
            )

            registry = build_tool_registry_from_file(registry_file=str(root_file))

        self.assertEqual(
            tuple(sorted(registry)),
            ("calc_eval", "calc_eval_fast", "task_retrieve"),
        )
        self.assertEqual(registry["calc_eval"].label, "Retrieval Calculator")

    def test_build_tool_registry_from_file_supports_registry_dirs_composition(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_dir = Path(tmpdir) / "registry-parts"
            registry_dir.mkdir()
            (registry_dir / "10-base.json").write_text(
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
            (registry_dir / "20-overlay.json").write_text(
                json.dumps(
                    {
                        "profile": "planning_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Planning Calculator",
                            }
                        },
                        "extra_tools": {
                            "mock_plan_brief": {
                                "template": "mock_plan",
                                "label": "Brief Planner",
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
                        "registry_dirs": [str(registry_dir)],
                    }
                ),
                encoding="utf-8",
            )

            registry = build_tool_registry_from_file(registry_file=str(root_file))

        self.assertEqual(
            tuple(sorted(registry)),
            ("calc_eval", "calc_eval_fast", "mock_plan_brief", "task_plan"),
        )
        self.assertEqual(registry["calc_eval"].label, "Planning Calculator")

    def test_build_tool_registry_from_file_resolves_relative_registry_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fixtures_dir = Path(tmpdir) / "fixtures"
            fixtures_dir.mkdir()
            nested_dir = fixtures_dir / "nested"
            nested_dir.mkdir()
            registry_dir = fixtures_dir / "registry-parts"
            registry_dir.mkdir()
            (registry_dir / "10-base.json").write_text(
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
            (registry_dir / "20-overlay.json").write_text(
                json.dumps(
                    {
                        "profile": "retrieval_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "label": "Retrieval Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            root_file = nested_dir / "root-manifest.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_dirs": ["../registry-parts"],
                    }
                ),
                encoding="utf-8",
            )

            registry = build_tool_registry_from_file(registry_file=str(root_file))

        self.assertEqual(
            tuple(sorted(registry)),
            ("calc_eval", "calc_eval_fast", "task_retrieve"),
        )
        self.assertEqual(registry["calc_eval"].label, "Retrieval Calculator")

    def test_build_tool_registry_from_file_supports_registry_sources_from_settings(self) -> None:
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
                        "registry_sources": ["planning_suite"],
                        "registry_files": [str(base_file)],
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
            ("calc_eval", "calc_eval_fast", "task_plan"),
        )
        self.assertEqual(registry["calc_eval"].label, "Planning Calculator")

    def test_build_tool_registry_from_file_accepts_tuple_registry_inputs_from_payload(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            base_file = Path(tmpdir) / "base-registry.json"
            overlay_file = Path(tmpdir) / "overlay-manifest.json"
            registry_dir = Path(tmpdir) / "registry-parts"
            registry_dir.mkdir()
            child_file = registry_dir / "10-child.json"
            for file_path in (root_file, base_file, overlay_file, child_file):
                file_path.write_text("{}", encoding="utf-8")

            settings = SimpleNamespace(
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "planning_suite": {
                            "provider_factory": "planning_only",
                            "overrides": {
                                "calc_eval": {
                                    "enabled": True,
                                    "label": "Source Calculator",
                                }
                            },
                        }
                    }
                )
            )
            original_loader = tool_runtime_module.load_tool_registry_file_payload
            try:
                def fake_load_tool_registry_file_payload(*, registry_file: str, base_dir=None):
                    resolved_registry_file = str(Path(registry_file).resolve())
                    if resolved_registry_file == str(root_file.resolve()):
                        return {
                            "registry_sources": ("planning_suite",),
                            "registry_files": (str(base_file), str(overlay_file)),
                            "registry_dirs": (str(registry_dir),),
                        }
                    if resolved_registry_file == str(base_file.resolve()):
                        return {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        }
                    if resolved_registry_file == str(overlay_file.resolve()):
                        return {
                            "profile": "planning_only",
                            "overrides": {
                                "calc_eval": {
                                    "enabled": True,
                                    "label": "Planning Calculator",
                                }
                            },
                        }
                    if resolved_registry_file == str(child_file.resolve()):
                        return {
                            "mock_plan_brief": {
                                "template": "mock_plan",
                                "label": "Brief Planner",
                            }
                        }
                    return original_loader(registry_file=registry_file, base_dir=base_dir)

                tool_runtime_module.load_tool_registry_file_payload = (  # type: ignore[attr-defined]
                    fake_load_tool_registry_file_payload
                )
                registry = build_tool_registry_from_file(
                    registry_file=str(root_file),
                    settings=settings,
                )
            finally:
                tool_runtime_module.load_tool_registry_file_payload = original_loader  # type: ignore[attr-defined]

        self.assertEqual(
            tuple(sorted(registry)),
            ("calc_eval", "calc_eval_fast", "mock_plan_brief", "task_plan"),
        )
        self.assertEqual(registry["calc_eval"].label, "Planning Calculator")

    def test_build_tool_registry_from_file_accepts_mapping_sequence_wrappers_from_payload(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            base_file = Path(tmpdir) / "base-registry.json"
            for file_path in (root_file, base_file):
                file_path.write_text("{}", encoding="utf-8")

            original_loader = tool_runtime_module.load_tool_registry_file_payload
            try:
                def fake_load_tool_registry_file_payload(*, registry_file: str, base_dir=None):
                    resolved_registry_file = str(Path(registry_file).resolve())
                    if resolved_registry_file == str(root_file.resolve()):
                        return UserDict(
                            {
                                UserString("profile"): UserString("default"),
                                UserString("registry_files"): UserList(
                                    [UserString(str(base_file))]
                                ),
                                UserString("disabled_tool_names"): UserList(
                                    [UserString("mock_plan")]
                                ),
                                UserString("extra_tools"): UserDict(
                                    {
                                        UserString("calc_eval_fast"): UserDict(
                                            {
                                                UserString("template"): UserString(
                                                    "calc_eval"
                                                ),
                                                UserString("label"): UserString(
                                                    "Fast Calculator"
                                                ),
                                            }
                                        )
                                    }
                                ),
                            }
                        )
                    if resolved_registry_file == str(base_file.resolve()):
                        return UserDict(
                            {
                                UserString("overrides"): UserDict(
                                    {
                                        UserString("calc_eval"): UserDict(
                                            {
                                                UserString("enabled"): True,
                                                UserString("label"): UserString(
                                                    "Planning Calculator"
                                                ),
                                            }
                                        )
                                    }
                                )
                            }
                        )
                    return original_loader(registry_file=registry_file, base_dir=base_dir)

                tool_runtime_module.load_tool_registry_file_payload = (  # type: ignore[attr-defined]
                    fake_load_tool_registry_file_payload
                )
                registry = build_tool_registry_from_file(registry_file=str(root_file))
            finally:
                tool_runtime_module.load_tool_registry_file_payload = original_loader  # type: ignore[attr-defined]

        self.assertEqual(
            tuple(sorted(registry)),
            ("calc_eval", "calc_eval_fast", "task_retrieve"),
        )
        self.assertEqual(registry["calc_eval"].label, "Planning Calculator")
        self.assertEqual(registry["calc_eval_fast"].label, "Fast Calculator")

    def test_build_tool_registry_from_file_artifacts_reports_missing_tuple_registry_inputs(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            root_file.write_text("{}", encoding="utf-8")
            missing_file = Path(tmpdir) / "missing-registry.json"
            missing_dir = Path(tmpdir) / "missing-dir"

            original_loader = tool_runtime_module.load_tool_registry_file_payload
            try:
                tool_runtime_module.load_tool_registry_file_payload = (  # type: ignore[attr-defined]
                    lambda *, registry_file, base_dir=None: {
                        "registry_sources": ("missing_suite",),
                        "registry_files": (str(missing_file),),
                        "registry_dirs": (str(missing_dir),),
                    }
                    if str(Path(registry_file).resolve()) == str(root_file.resolve())
                    else original_loader(registry_file=registry_file, base_dir=base_dir)
                )
                artifacts = build_tool_registry_from_file_artifacts(
                    registry_file=str(root_file)
                )
            finally:
                tool_runtime_module.load_tool_registry_file_payload = original_loader  # type: ignore[attr-defined]

        diagnostics = artifacts["diagnostics"]
        self.assertEqual(diagnostics["missing_registry_sources"], ("missing_suite",))
        self.assertEqual(
            diagnostics["missing_registry_files"],
            (str(missing_file.resolve()),),
        )
        self.assertEqual(
            diagnostics["missing_registry_dirs"],
            (str(missing_dir.resolve()),),
        )

    def test_build_tool_registry_from_file_reuses_shared_provider_source_name_helper_for_registry_sources(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_sources": [" Planning_Suite "],
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "planning_suite_shadow": {
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
            original_get_tool_registry_provider_source_name_from_settings = (
                tool_runtime_module.get_tool_registry_provider_source_name_from_settings
            )
            captured: list[object] = []
            try:
                def fake_get_tool_registry_provider_source_name_from_settings(
                    *,
                    settings=None,
                ):
                    captured.append(
                        getattr(settings, "tool_registry_provider_source", None)
                    )
                    if (
                        getattr(settings, "tool_registry_provider_source", None)
                        == " Planning_Suite "
                    ):
                        return "planning_suite_shadow"
                    return original_get_tool_registry_provider_source_name_from_settings(
                        settings=settings
                    )

                tool_runtime_module.get_tool_registry_provider_source_name_from_settings = (
                    fake_get_tool_registry_provider_source_name_from_settings
                )
                registry = build_tool_registry_from_file(
                    registry_file=str(root_file),
                    settings=settings,
                )
            finally:
                tool_runtime_module.get_tool_registry_provider_source_name_from_settings = (
                    original_get_tool_registry_provider_source_name_from_settings
                )

        self.assertIn(" Planning_Suite ", captured)
        self.assertEqual(
            tuple(sorted(registry)),
            ("calc_eval", "task_plan"),
        )
        self.assertEqual(registry["calc_eval"].label, "Planning Calculator")

    def test_build_tool_registry_loader_from_file_supports_registry_sources_from_settings(self) -> None:
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
                )
            )

            loader = build_tool_registry_loader_from_file(
                registry_file=str(root_file),
                settings=settings,
            )
            self.assertIsNotNone(loader)
            registry = loader()

        self.assertEqual(
            tuple(sorted(registry)),
            ("calc_eval", "calc_eval_fast", "task_plan"),
        )
        self.assertEqual(registry["calc_eval"].label, "Planning Calculator")

    def test_build_tool_registry_loader_from_file_supports_registry_sources_backed_by_named_provider(
        self,
    ) -> None:
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
                tool_registry_providers_json=json.dumps(
                    {
                        "planning_provider": {
                            "loader": "default",
                            "profile": "planning_only",
                            "overrides": {
                                "calc_eval": {
                                    "enabled": True,
                                    "label": "Planning Calculator",
                                }
                            },
                        }
                    }
                ),
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "planning_suite": {
                            "provider": "planning_provider",
                        }
                    }
                ),
            )

            loader = build_tool_registry_loader_from_file(
                registry_file=str(root_file),
                settings=settings,
            )
            self.assertIsNotNone(loader)
            registry = loader()

        self.assertEqual(
            tuple(sorted(registry)),
            ("calc_eval", "calc_eval_fast", "task_plan"),
        )
        self.assertEqual(registry["calc_eval"].label, "Planning Calculator")

    def test_build_tool_registry_loader_from_file_registry_sources_named_provider_file_uses_child_source_context(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            child_file = Path(tmpdir) / "child-source-registry.json"
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
                                "kind": "provider_retrieval",
                                "runtime_semantic_kind": "provider_search",
                                "execution": {
                                    "kind": "http_json",
                                    "url": "https://provider.example/search",
                                    "query_params": {
                                        "source": "$tool_registry_provider_source",
                                        "q": "$query",
                                    },
                                    "result_fields": {
                                        "documents_total": "$.meta.total",
                                    },
                                },
                                "result_preview_keys": ["documents_total"],
                                "result_output_keys": ["documents_total"],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source="global_selected",
                tool_registry_providers_json=json.dumps(
                    {
                        "search_provider": {
                            "registry_file": str(child_file),
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

            loader = build_tool_registry_loader_from_file(
                registry_file=str(root_file),
                settings=settings,
            )
            self.assertIsNotNone(loader)
            registry = loader()
            provider = StaticToolRegistryProvider(registry=registry)
            urlopen_calls: list[object] = []

            class FakeHttpResponse:
                def read(self) -> bytes:
                    return b'{"meta":{"total":14}}'

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
                    tool_input={"query": "child source cash flow"},
                    prompt="search child source cash flow",
                    user_id="user-1",
                    attempt=0,
                    registry_provider=provider,
                )
            finally:
                if original_urlopen is None:
                    delattr(tool_runtime_module, "urlopen")
                else:
                    tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(output["documents_total"], 14)
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        self.assertEqual(
            request.full_url,
            "https://provider.example/search?source=search_suite&q=child+source+cash+flow",
        )
