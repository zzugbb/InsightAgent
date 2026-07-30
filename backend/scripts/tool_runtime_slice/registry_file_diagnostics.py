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

    def test_build_tool_registry_from_file_ignores_registry_dir_replayed_via_relative_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fixtures_dir = Path(tmpdir) / "fixtures"
            fixtures_dir.mkdir()
            nested_dir = fixtures_dir / "nested"
            nested_dir.mkdir()
            registry_dir = fixtures_dir / "registry-parts"
            registry_dir.mkdir()
            (registry_dir / "10-overlay.json").write_text(
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
                        "registry_dirs": [
                            str(registry_dir),
                            "../registry-parts",
                        ],
                    }
                ),
                encoding="utf-8",
            )

            registry = build_tool_registry_from_file(registry_file=str(root_file))

        self.assertEqual(
            tuple(sorted(registry)),
            ("calc_eval", "task_retrieve"),
        )
        self.assertEqual(registry["calc_eval"].label, "Retrieval Calculator")

    def test_build_tool_registry_from_file_artifacts_reports_skipped_duplicate_inputs(self) -> None:
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
                        "registry_sources": ["planning_suite", "planning_suite"],
                        "registry_files": [str(base_file), str(base_file), str(root_file)],
                        "registry_dirs": [str(registry_dir), str(registry_dir)],
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "planning_suite": {
                            "provider_factory": "planning_only",
                        }
                    }
                )
            )

            artifacts = build_tool_registry_from_file_artifacts(
                registry_file=str(root_file),
                settings=settings,
            )

        self.assertEqual(
            tuple(sorted(artifacts["registry"])),
            ("calc_eval", "calc_eval_fast", "task_plan"),
        )
        diagnostics = artifacts["diagnostics"]
        self.assertEqual(diagnostics["skipped_registry_sources"], ("planning_suite",))
        self.assertEqual(
            diagnostics["skipped_registry_files"],
            (str(base_file.resolve()), str(root_file.resolve())),
        )
        self.assertEqual(diagnostics["skipped_registry_dirs"], (str(registry_dir.resolve()),))

    def test_build_tool_registry_from_file_artifacts_reports_missing_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            missing_dir = Path(tmpdir) / "missing-registry-dir"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_sources": ["missing_suite"],
                        "registry_files": [str(missing_file)],
                        "registry_dirs": [str(missing_dir)],
                    }
                ),
                encoding="utf-8",
            )

            artifacts = build_tool_registry_from_file_artifacts(
                registry_file=str(root_file),
                settings=SimpleNamespace(tool_registry_provider_sources_json=json.dumps({})),
            )

        self.assertEqual(artifacts["registry"], {})
        diagnostics = artifacts["diagnostics"]
        self.assertEqual(diagnostics["missing_registry_sources"], ("missing_suite",))
        self.assertEqual(
            diagnostics["missing_registry_files"],
            (str(missing_file.resolve()),),
        )
        self.assertEqual(diagnostics["missing_registry_dirs"], (str(missing_dir.resolve()),))

    def test_build_tool_registry_loader_from_file_artifacts_exposes_loader_and_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
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

            artifacts = build_tool_registry_loader_from_file_artifacts(
                registry_file=str(root_file)
            )

        self.assertIsNotNone(artifacts["loader"])
        self.assertEqual(tuple(sorted(artifacts["registry"])), ("calc_eval_fast",))
        self.assertEqual(
            artifacts["loader"](),
            artifacts["registry"],
        )
        self.assertEqual(
            artifacts["diagnostics"]["missing_registry_files"],
            (str(missing_file.resolve()),),
        )

    def test_build_tool_registry_provider_from_file_artifacts_exposes_provider_and_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_dir = Path(tmpdir) / "missing-registry-dir"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_dirs": [str(missing_dir)],
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

            artifacts = build_tool_registry_provider_from_file_artifacts(
                registry_file=str(root_file)
            )

        self.assertIsNotNone(artifacts["provider"])
        self.assertEqual(tuple(sorted(artifacts["registry"])), ("calc_eval_fast",))
        self.assertEqual(
            artifacts["provider"].load_tool_registry(),
            artifacts["registry"],
        )
        self.assertEqual(
            artifacts["diagnostics"]["missing_registry_dirs"],
            (str(missing_dir.resolve()),),
        )

    def test_build_tool_registry_loaders_from_settings_artifacts_tracks_file_loader_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
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
                tool_registry_loaders_json=json.dumps(
                    {
                        "file_loader": {
                            "registry_file": str(root_file),
                        }
                    }
                )
            )

            artifacts = build_tool_registry_loaders_from_settings_artifacts(settings=settings)

        self.assertEqual(tuple(sorted(artifacts["loaders"])), ("file_loader",))
        self.assertEqual(
            artifacts["loader_diagnostics"]["file_loader"]["missing_registry_files"],
            (str(missing_file.resolve()),),
        )
        self.assertEqual(
            tuple(sorted(artifacts["loaders"]["file_loader"]())),
            ("calc_eval_fast",),
        )

    def test_build_tool_registry_loaders_from_settings_artifacts_tracks_loader_override_execution_diagnostics(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_loaders_json=json.dumps(
                {
                    "search_loader": {
                        "extra_tools": {
                            "provider_search": {
                                "template": "task_retrieve",
                                "label": "Provider Search",
                            }
                        },
                        "overrides": {
                            "provider_search": {
                                "execution": {
                                    "kind": "http_json",
                                    "url": "https://provider.example/search",
                                    "headers": {
                                        "Authorization": "Bearer ${settings_api_keey}",
                                    },
                                },
                            }
                        },
                    }
                }
            )
        )

        artifacts = build_tool_registry_loaders_from_settings_artifacts(settings=settings)

        self.assertEqual(tuple(sorted(artifacts["loaders"])), ("search_loader",))
        self.assertIn(
            (
                "provider_search: http_json execution references unsupported runtime "
                "template variable settings_api_keey in [redacted]"
            ),
            artifacts["loader_diagnostics"]["search_loader"]["invalid_tool_executions"],
        )

    def test_build_tool_registry_loaders_from_settings_artifacts_keeps_missing_file_diagnostics_when_loader_unbuilt(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_file = Path(tmpdir) / "missing-loader-registry.json"
            settings = SimpleNamespace(
                tool_registry_loaders_json=json.dumps(
                    {
                        "file_loader": {
                            "registry_file": str(missing_file),
                        }
                    }
                )
            )

            artifacts = build_tool_registry_loaders_from_settings_artifacts(
                settings=settings
            )

        self.assertEqual(artifacts["loaders"], {})
        self.assertEqual(
            artifacts["loader_diagnostics"]["file_loader"]["missing_registry_files"],
            (str(missing_file.resolve()),),
        )

    def test_build_tool_registry_loader_factories_from_settings_artifacts_tracks_registry_file_diagnostics(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
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
                tool_registry_loader_factories_json=json.dumps(
                    {
                        "file_factory": {
                            "registry_file": str(root_file),
                        }
                    }
                )
            )

            artifacts = build_tool_registry_loader_factories_from_settings_artifacts(
                settings=settings
            )

        self.assertEqual(tuple(sorted(artifacts["loader_factories"])), ("file_factory",))
        self.assertEqual(
            artifacts["loader_factory_diagnostics"]["file_factory"]["missing_registry_files"],
            (str(missing_file.resolve()),),
        )

    def test_build_tool_registry_loader_factories_from_settings_artifacts_tracks_factory_override_execution_diagnostics(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "loader-factory-override-diagnostics.json"
            registry_file.write_text(
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
                tool_registry_loader_factories_json=json.dumps(
                    {
                        "file_factory": {
                            "registry_file": str(registry_file),
                            "overrides": {
                                "provider_search": {
                                    "execution": {
                                        "kind": "http_json",
                                        "url": "https://provider.example/search",
                                        "headers": {
                                            "Authorization": "Bearer ${settings_api_keey}",
                                        },
                                    },
                                }
                            },
                        }
                    }
                )
            )

            artifacts = build_tool_registry_loader_factories_from_settings_artifacts(
                settings=settings
            )

        self.assertEqual(tuple(sorted(artifacts["loader_factories"])), ("file_factory",))
        self.assertIn(
            (
                "provider_search: http_json execution references unsupported runtime "
                "template variable settings_api_keey in [redacted]"
            ),
            artifacts["loader_factory_diagnostics"]["file_factory"][
                "invalid_tool_executions"
            ],
        )

    def test_build_tool_registry_loader_factories_from_settings_artifacts_tracks_alias_factory_override_execution_diagnostics(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "loader-factory-alias-diagnostics.json"
            registry_file.write_text(
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
                tool_registry_loader_factories_json=json.dumps(
                    {
                        "outer_factory": {
                            "factory": "inner_factory",
                            "overrides": {
                                "provider_search": {
                                    "execution": {
                                        "kind": "http_json",
                                        "url": "https://provider.example/search",
                                        "headers": {
                                            "Authorization": "Bearer ${settings_api_keey}",
                                        },
                                    },
                                }
                            },
                        },
                        "inner_factory": {
                            "registry_file": str(registry_file),
                        },
                    }
                )
            )

            artifacts = build_tool_registry_loader_factories_from_settings_artifacts(
                settings=settings
            )

        self.assertEqual(
            tuple(sorted(artifacts["loader_factories"])),
            ("inner_factory", "outer_factory"),
        )
        self.assertIn(
            (
                "provider_search: http_json execution references unsupported runtime "
                "template variable settings_api_keey in [redacted]"
            ),
            artifacts["loader_factory_diagnostics"]["outer_factory"][
                "invalid_tool_executions"
            ],
        )

    def test_build_tool_registry_loader_factories_from_settings_artifacts_tracks_alias_profile_factory_reenabled_override_execution_diagnostics(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_loader_factories_json=json.dumps(
                {
                    "outer_factory": {
                        "factory": "retrieval_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "execution": {
                                    "kind": "http_json",
                                    "url": "https://provider.example/calc",
                                    "headers": {
                                        "Authorization": "Bearer ${settings_api_keey}",
                                    },
                                },
                            }
                        },
                    }
                }
            )
        )

        artifacts = build_tool_registry_loader_factories_from_settings_artifacts(
            settings=settings
        )

        self.assertEqual(tuple(sorted(artifacts["loader_factories"])), ("outer_factory",))
        self.assertIn(
            (
                "calc_eval: http_json execution references unsupported runtime "
                "template variable settings_api_keey in [redacted]"
            ),
            artifacts["loader_factory_diagnostics"]["outer_factory"][
                "invalid_tool_executions"
            ],
        )

    def test_build_tool_registry_loader_factories_from_settings_artifacts_keeps_missing_file_diagnostics_when_factory_unbuilt(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_file = Path(tmpdir) / "missing-loader-factory-registry.json"
            settings = SimpleNamespace(
                tool_registry_loader_factories_json=json.dumps(
                    {
                        "file_factory": {
                            "registry_file": str(missing_file),
                        }
                    }
                )
            )

            artifacts = build_tool_registry_loader_factories_from_settings_artifacts(
                settings=settings
            )

        self.assertEqual(artifacts["loader_factories"], {})
        self.assertEqual(
            artifacts["loader_factory_diagnostics"]["file_factory"]["missing_registry_files"],
            (str(missing_file.resolve()),),
        )

    def test_build_tool_registry_provider_factories_from_settings_artifacts_tracks_registry_file_diagnostics(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_dir = Path(tmpdir) / "missing-registry-dir"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_dirs": [str(missing_dir)],
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
                tool_registry_provider_factories_json=json.dumps(
                    {
                        "file_factory": {
                            "registry_file": str(root_file),
                        }
                    }
                )
            )

            artifacts = build_tool_registry_provider_factories_from_settings_artifacts(
                settings=settings
            )

        self.assertEqual(tuple(sorted(artifacts["provider_factories"])), ("file_factory",))
        self.assertEqual(
            artifacts["provider_factory_diagnostics"]["file_factory"]["missing_registry_dirs"],
            (str(missing_dir.resolve()),),
        )

    def test_build_tool_registry_provider_factories_from_settings_artifacts_tracks_factory_override_execution_diagnostics(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "provider-factory-override-diagnostics.json"
            registry_file.write_text(
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
                tool_registry_provider_factories_json=json.dumps(
                    {
                        "file_factory": {
                            "registry_file": str(registry_file),
                            "overrides": {
                                "provider_search": {
                                    "execution": {
                                        "kind": "http_json",
                                        "url": "https://provider.example/search",
                                        "headers": {
                                            "Authorization": "Bearer ${settings_api_keey}",
                                        },
                                    },
                                }
                            },
                        }
                    }
                )
            )

            artifacts = build_tool_registry_provider_factories_from_settings_artifacts(
                settings=settings
            )

        self.assertEqual(tuple(sorted(artifacts["provider_factories"])), ("file_factory",))
        self.assertIn(
            (
                "provider_search: http_json execution references unsupported runtime "
                "template variable settings_api_keey in [redacted]"
            ),
            artifacts["provider_factory_diagnostics"]["file_factory"][
                "invalid_tool_executions"
            ],
        )

    def test_build_tool_registry_provider_factories_from_settings_artifacts_tracks_alias_factory_override_execution_diagnostics(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "provider-factory-alias-diagnostics.json"
            registry_file.write_text(
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
                tool_registry_provider_factories_json=json.dumps(
                    {
                        "outer_factory": {
                            "factory": "inner_factory",
                            "overrides": {
                                "provider_search": {
                                    "execution": {
                                        "kind": "http_json",
                                        "url": "https://provider.example/search",
                                        "headers": {
                                            "Authorization": "Bearer ${settings_api_keey}",
                                        },
                                    },
                                }
                            },
                        },
                        "inner_factory": {
                            "registry_file": str(registry_file),
                        },
                    }
                )
            )

            artifacts = build_tool_registry_provider_factories_from_settings_artifacts(
                settings=settings
            )

        self.assertEqual(
            tuple(sorted(artifacts["provider_factories"])),
            ("inner_factory", "outer_factory"),
        )
        self.assertIn(
            (
                "provider_search: http_json execution references unsupported runtime "
                "template variable settings_api_keey in [redacted]"
            ),
            artifacts["provider_factory_diagnostics"]["outer_factory"][
                "invalid_tool_executions"
            ],
        )

    def test_build_tool_registry_provider_factories_from_settings_artifacts_tracks_alias_profile_factory_reenabled_override_execution_diagnostics(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_factories_json=json.dumps(
                {
                    "outer_factory": {
                        "factory": "retrieval_only",
                        "overrides": {
                            "calc_eval": {
                                "enabled": True,
                                "execution": {
                                    "kind": "http_json",
                                    "url": "https://provider.example/calc",
                                    "headers": {
                                        "Authorization": "Bearer ${settings_api_keey}",
                                    },
                                },
                            }
                        },
                    }
                }
            )
        )

        artifacts = build_tool_registry_provider_factories_from_settings_artifacts(
            settings=settings
        )

        self.assertEqual(tuple(sorted(artifacts["provider_factories"])), ("outer_factory",))
        self.assertIn(
            (
                "calc_eval: http_json execution references unsupported runtime "
                "template variable settings_api_keey in [redacted]"
            ),
            artifacts["provider_factory_diagnostics"]["outer_factory"][
                "invalid_tool_executions"
            ],
        )

    def test_build_tool_registry_provider_factories_from_settings_artifacts_keeps_missing_file_diagnostics_when_factory_unbuilt(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_file = Path(tmpdir) / "missing-provider-factory-registry.json"
            settings = SimpleNamespace(
                tool_registry_provider_factories_json=json.dumps(
                    {
                        "file_factory": {
                            "registry_file": str(missing_file),
                        }
                    }
                )
            )

            artifacts = build_tool_registry_provider_factories_from_settings_artifacts(
                settings=settings
            )

        self.assertEqual(artifacts["provider_factories"], {})
        self.assertEqual(
            artifacts["provider_factory_diagnostics"]["file_factory"]["missing_registry_files"],
            (str(missing_file.resolve()),),
        )

    def test_build_tool_registry_providers_from_settings_artifacts_tracks_loader_factory_diagnostics(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
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
                tool_registry_loader_factories_json=json.dumps(
                    {
                        "file_factory": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
                tool_registry_providers_json=json.dumps(
                    {
                        "file_provider": {
                            "loader_factory": "file_factory",
                        }
                    }
                ),
            )

            artifacts = build_tool_registry_providers_from_settings_artifacts(
                settings=settings
            )

        self.assertEqual(tuple(sorted(artifacts["providers"])), ("file_provider",))
        self.assertEqual(
            artifacts["provider_diagnostics"]["file_provider"]["missing_registry_files"],
            (str(missing_file.resolve()),),
        )
        self.assertEqual(
            tuple(sorted(artifacts["providers"]["file_provider"].load_tool_registry())),
            ("calc_eval_fast",),
        )

    def test_build_tool_registry_providers_from_settings_artifacts_keeps_missing_file_diagnostics_when_provider_unbuilt(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_file = Path(tmpdir) / "missing-provider-registry.json"
            settings = SimpleNamespace(
                tool_registry_providers_json=json.dumps(
                    {
                        "file_provider": {
                            "registry_file": str(missing_file),
                        }
                    }
                )
            )

            artifacts = build_tool_registry_providers_from_settings_artifacts(
                settings=settings
            )

        self.assertEqual(artifacts["providers"], {})
        self.assertEqual(
            artifacts["provider_diagnostics"]["file_provider"]["missing_registry_files"],
            (str(missing_file.resolve()),),
        )

    def test_build_tool_registry_providers_from_settings_artifacts_tracks_provider_override_execution_diagnostics(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_providers_json=json.dumps(
                {
                    "search_provider": {
                        "extra_tools": {
                            "provider_search": {
                                "template": "task_retrieve",
                                "label": "Provider Search",
                            }
                        },
                        "overrides": {
                            "provider_search": {
                                "execution": {
                                    "kind": "http_json",
                                    "url": "https://provider.example/search",
                                    "headers": {
                                        "Authorization": "Bearer ${settings_api_keey}",
                                    },
                                },
                            }
                        },
                    }
                }
            )
        )

        artifacts = build_tool_registry_providers_from_settings_artifacts(settings=settings)

        self.assertEqual(tuple(sorted(artifacts["providers"])), ("search_provider",))
        self.assertIn(
            (
                "provider_search: http_json execution references unsupported runtime "
                "template variable settings_api_keey in [redacted]"
            ),
            artifacts["provider_diagnostics"]["search_provider"][
                "invalid_tool_executions"
            ],
        )

    def test_build_tool_registry_provider_sources_from_settings_artifacts_tracks_named_provider_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_dir = Path(tmpdir) / "missing-registry-dir"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_dirs": [str(missing_dir)],
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
                        "file_provider": {
                            "registry_file": str(root_file),
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

            artifacts = build_tool_registry_provider_sources_from_settings_artifacts(
                settings=settings
            )

        self.assertEqual(tuple(sorted(artifacts["sources"])), ("file_source",))
        self.assertEqual(
            artifacts["source_diagnostics"]["file_source"]["missing_registry_dirs"],
            (str(missing_dir.resolve()),),
        )
        self.assertEqual(
            tuple(sorted(artifacts["sources"]["file_source"].load_tool_registry())),
            ("calc_eval_fast",),
        )

    def test_build_tool_registry_provider_sources_from_settings_artifacts_tracks_named_source_diagnostics(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_file = Path(tmpdir) / "missing-inner-source-registry.json"
            settings = SimpleNamespace(
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "inner_source": {
                            "registry_file": str(missing_file),
                        },
                        "outer_source": {
                            "provider": "inner_source",
                        },
                    }
                )
            )

            artifacts = build_tool_registry_provider_sources_from_settings_artifacts(
                settings=settings
            )

        self.assertEqual(artifacts["sources"], {})
        self.assertEqual(
            artifacts["source_diagnostics"]["outer_source"]["missing_registry_files"],
            (str(missing_file.resolve()),),
        )

    def test_build_tool_registry_provider_sources_from_settings_artifacts_reuse_shared_reference_normalizer_for_named_provider_diagnostics(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_dir = Path(tmpdir) / "missing-registry-dir"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_dirs": [str(missing_dir)],
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
                        "planning_provider_shadow": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "planning_suite": {
                            "provider": " Planning_Provider ",
                        }
                    }
                ),
            )
            original_resolve_named_tool_registry_provider_reference = (
                tool_runtime_module.resolve_named_tool_registry_provider_reference
            )
            original_normalize_named_tool_registry_component_name = getattr(
                tool_runtime_module,
                "_normalize_named_tool_registry_component_name",
                None,
            )
            captured: list[object] = []
            try:
                def fake_normalize_named_tool_registry_component_name(
                    name: object | None,
                ) -> str | None:
                    captured.append(name)
                    if name == " Planning_Provider ":
                        return "planning_provider_shadow"
                    if not isinstance(name, str):
                        return None
                    normalized = name.strip().lower()
                    return normalized or None

                def fake_resolve_named_tool_registry_provider_reference(
                    name: str,
                    *,
                    named_providers=None,
                    named_sources=None,
                ):
                    if name == " Planning_Provider " and named_providers is not None:
                        return named_providers.get("planning_provider_shadow")
                    return original_resolve_named_tool_registry_provider_reference(
                        name,
                        named_providers=named_providers,
                        named_sources=named_sources,
                    )

                tool_runtime_module._normalize_named_tool_registry_component_name = (
                    fake_normalize_named_tool_registry_component_name
                )
                tool_runtime_module.resolve_named_tool_registry_provider_reference = (
                    fake_resolve_named_tool_registry_provider_reference
                )
                artifacts = build_tool_registry_provider_sources_from_settings_artifacts(
                    settings=settings
                )
            finally:
                tool_runtime_module.resolve_named_tool_registry_provider_reference = (
                    original_resolve_named_tool_registry_provider_reference
                )
                if original_normalize_named_tool_registry_component_name is None:
                    delattr(
                        tool_runtime_module,
                        "_normalize_named_tool_registry_component_name",
                    )
                else:
                    tool_runtime_module._normalize_named_tool_registry_component_name = (
                        original_normalize_named_tool_registry_component_name
                    )

        self.assertIn(" Planning_Provider ", captured)
        self.assertEqual(tuple(sorted(artifacts["sources"])), ("planning_suite",))
        self.assertEqual(
            artifacts["source_diagnostics"]["planning_suite"]["missing_registry_dirs"],
            (str(missing_dir.resolve()),),
        )
        self.assertEqual(
            tuple(sorted(artifacts["sources"]["planning_suite"].load_tool_registry())),
            ("calc_eval_fast",),
        )

    def test_build_tool_registry_provider_sources_from_settings_artifacts_tracks_loader_factory_diagnostics(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
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
                tool_registry_loader_factories_json=json.dumps(
                    {
                        "file_factory": {
                            "registry_file": str(root_file),
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

            artifacts = build_tool_registry_provider_sources_from_settings_artifacts(
                settings=settings
            )

        self.assertEqual(tuple(sorted(artifacts["sources"])), ("file_source",))
        self.assertEqual(
            artifacts["source_diagnostics"]["file_source"]["missing_registry_files"],
            (str(missing_file.resolve()),),
        )
        self.assertEqual(
            tuple(sorted(artifacts["sources"]["file_source"].load_tool_registry())),
            ("calc_eval_fast",),
        )

    def test_get_configured_tool_registry_provider_artifacts_exposes_selected_source_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
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
                tool_registry_provider_source="file_source",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "file_source": {
                            "registry_file": str(root_file),
                        }
                    }
                ),
            )

            artifacts = get_configured_tool_registry_provider_artifacts(settings=settings)

        self.assertEqual(artifacts["provider_source_name"], "file_source")
        self.assertEqual(
            artifacts["selected_source_diagnostics"]["missing_registry_files"],
            (str(missing_file.resolve()),),
        )
        self.assertEqual(
            tuple(sorted(artifacts["provider"].load_tool_registry())),
            ("calc_eval_fast",),
        )

    def test_get_configured_tool_registry_provider_artifacts_exposes_selected_source_diagnostics_for_loader_factory_source(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root_file = Path(tmpdir) / "root-manifest.json"
            missing_file = Path(tmpdir) / "missing-registry.json"
            root_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
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
                tool_registry_provider_source="file_source",
                tool_registry_loader_factories_json=json.dumps(
                    {
                        "file_factory": {
                            "registry_file": str(root_file),
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

            artifacts = get_configured_tool_registry_provider_artifacts(settings=settings)

        self.assertEqual(artifacts["provider_source_name"], "file_source")
        self.assertEqual(
            artifacts["selected_source_diagnostics"]["missing_registry_files"],
            (str(missing_file.resolve()),),
        )
        self.assertEqual(
            tuple(sorted(artifacts["provider"].load_tool_registry())),
            ("calc_eval_fast",),
        )

    def test_get_configured_tool_registry_provider_artifacts_exposes_selected_source_factory_override_execution_diagnostics(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "factory-override-diagnostics.json"
            registry_file.write_text(
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
                tool_registry_provider_source="file_source",
                tool_registry_loader_factories_json=json.dumps(
                    {
                        "file_factory": {
                            "registry_file": str(registry_file),
                            "overrides": {
                                "provider_search": {
                                    "execution": {
                                        "kind": "http_json",
                                        "url": "https://provider.example/search",
                                        "headers": {
                                            "Authorization": "Bearer ${settings_api_keey}",
                                        },
                                    },
                                }
                            },
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

            artifacts = get_configured_tool_registry_provider_artifacts(settings=settings)

        self.assertEqual(artifacts["provider_source_name"], "file_source")
        self.assertIn(
            (
                "provider_search: http_json execution references unsupported runtime "
                "template variable settings_api_keey in [redacted]"
            ),
            artifacts["selected_source_diagnostics"]["invalid_tool_executions"],
        )
        self.assertIn(
            "provider_search",
            artifacts["provider"].load_tool_registry(),
        )

    def test_get_configured_tool_registry_provider_artifacts_exposes_selected_source_override_execution_diagnostics(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_source="file_source",
            tool_registry_provider_sources_json=json.dumps(
                {
                    "file_source": {
                        "provider": "default",
                        "extra_tools": {
                            "provider_search": {
                                "template": "task_retrieve",
                                "label": "Provider Search",
                            }
                        },
                        "overrides": {
                            "provider_search": {
                                "execution": {
                                    "kind": "http_json",
                                    "url": "https://provider.example/search",
                                    "headers": {
                                        "Authorization": "Bearer ${settings_api_keey}",
                                    },
                                },
                            }
                        },
                    }
                }
            ),
        )

        artifacts = get_configured_tool_registry_provider_artifacts(settings=settings)

        self.assertEqual(artifacts["provider_source_name"], "file_source")
        self.assertIn(
            (
                "provider_search: http_json execution references unsupported runtime "
                "template variable settings_api_keey in [redacted]"
            ),
            artifacts["selected_source_diagnostics"]["invalid_tool_executions"],
        )
        self.assertIn(
            "provider_search",
            artifacts["provider"].load_tool_registry(),
        )

    def test_build_tool_registry_diagnostics_summary_keeps_shape(self) -> None:
        diagnostics = {
            "skipped_registry_sources": ("planning_suite",),
            "missing_registry_sources": (),
            "skipped_registry_files": ("/tmp/base.json",),
            "missing_registry_files": ("/tmp/missing.json",),
            "skipped_registry_dirs": (),
            "missing_registry_dirs": ("/tmp/missing-dir",),
        }

        result = build_tool_registry_diagnostics_summary(diagnostics=diagnostics)

        self.assertTrue(result["has_diagnostics"])
        self.assertEqual(result["skipped_total"], 2)
        self.assertEqual(result["missing_total"], 2)
        self.assertEqual(result["total"], 4)
        self.assertEqual(
            result["entries"],
            (
                {
                    "kind": "skipped",
                    "target": "registry_sources",
                    "count": 1,
                    "values": ("planning_suite",),
                },
                {
                    "kind": "skipped",
                    "target": "registry_files",
                    "count": 1,
                    "values": ("/tmp/base.json",),
                },
                {
                    "kind": "missing",
                    "target": "registry_files",
                    "count": 1,
                    "values": ("/tmp/missing.json",),
                },
                {
                    "kind": "missing",
                    "target": "registry_dirs",
                    "count": 1,
                    "values": ("/tmp/missing-dir",),
                },
            ),
        )

    def test_build_tool_registry_diagnostics_summary_includes_invalid_tool_execution_entries(
        self,
    ) -> None:
        diagnostics = {
            "skipped_registry_sources": (),
            "missing_registry_sources": (),
            "skipped_registry_files": (),
            "missing_registry_files": (),
            "skipped_registry_dirs": (),
            "missing_registry_dirs": (),
            "invalid_tool_executions": (
                "provider_search: unsupported tool execution kind unsupported_transport",
            ),
        }

        result = build_tool_registry_diagnostics_summary(diagnostics=diagnostics)

        self.assertTrue(result["has_diagnostics"])
        self.assertEqual(result["skipped_total"], 0)
        self.assertEqual(result["missing_total"], 0)
        self.assertEqual(result["total"], 1)
        self.assertEqual(
            result["entries"],
            (
                {
                    "kind": "invalid",
                    "target": "tool_executions",
                    "count": 1,
                    "values": (
                        "provider_search: unsupported tool execution kind unsupported_transport",
                    ),
                },
            ),
        )

    def test_build_tool_registry_settings_execution_diagnostics_accepts_renderable_http_json_url_template(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
                base_url="https://gateway.example/v1",
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "${settings_base_url}/search",
                                "query_params": {
                                    "q": "$query",
                                },
                            },
                        }
                    }
                ),
            )
        )

        self.assertEqual(diagnostics["invalid_tool_executions"], ())

    def test_build_tool_registry_settings_execution_diagnostics_redacts_sensitive_execution_kind(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "token=hidden",
                            },
                        }
                    }
                ),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: unsupported tool execution kind [redacted]",
            ),
        )
        joined_diagnostics = "\n".join(diagnostics["invalid_tool_executions"])
        self.assertNotIn("token", joined_diagnostics)
        self.assertNotIn("hidden", joined_diagnostics)

    def test_build_tool_registry_settings_execution_diagnostics_rejects_http_json_url_credentials_without_summary_leak(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://token:secret@provider.example/search",
                        },
                    }
                }
            )
        )

        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=settings
        )
        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution url must not include credentials",
            ),
        )
        self.assertEqual(
            extra_tools["provider_search"].execution_summary,
            {
                "method": "GET",
                "url_origin": "https://provider.example",
                "url_path": "/search",
            },
        )
        self.assertNotIn(
            "token",
            json.dumps(extra_tools["provider_search"].execution_summary),
        )
        self.assertNotIn(
            "secret",
            json.dumps(extra_tools["provider_search"].execution_summary),
        )

    def test_build_tool_registry_settings_execution_diagnostics_rejects_http_json_url_invalid_port_without_summary_crash(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example:bad/search",
                        },
                    }
                }
            )
        )

        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=settings
        )
        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution url must include a valid port when port is provided",
            ),
        )
        self.assertEqual(
            extra_tools["provider_search"].execution_summary,
            {
                "method": "GET",
                "url_path": "/search",
            },
        )

    def test_build_tool_registry_settings_execution_diagnostics_rejects_http_json_url_control_characters_without_echo(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search path",
                        },
                    }
                }
            )
        )

        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=settings
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution url must not contain control characters or spaces",
            ),
        )
        self.assertNotIn(
            "search path",
            "\n".join(diagnostics["invalid_tool_executions"]),
        )

    def test_build_tool_registry_settings_execution_diagnostics_rejects_rendered_http_json_header_injection_without_echo(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
                api_key="sk-live\r\nX-Injected: yes",
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/search",
                                "headers": {
                                    "Authorization": "Bearer ${settings_api_key}",
                                },
                            },
                        }
                    }
                ),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution headers.Authorization must not contain CR or LF",
            ),
        )
        self.assertNotIn("Injected", "\n".join(diagnostics["invalid_tool_executions"]))

    def test_build_tool_registry_settings_execution_diagnostics_rejects_http_json_header_control_characters_without_echo(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/search",
                                "headers": {
                                    "X-Trace": "ok\x00bad",
                                },
                            },
                        }
                    }
                ),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution headers.X-Trace must not contain control characters",
            ),
        )
        self.assertNotIn("ok\x00bad", "\n".join(diagnostics["invalid_tool_executions"]))

    def test_build_tool_registry_settings_execution_diagnostics_redacts_sensitive_request_field_paths(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/search",
                                "query_params": {
                                    "api_key": {"raw": "bad"},
                                },
                                "json_body": {
                                    "access_token": float("nan"),
                                    "filters": [
                                        {
                                            "client_secret": float("inf"),
                                        }
                                    ],
                                },
                            },
                        }
                    }
                ),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution query_params.[redacted] must be a string, number, boolean, or list of those values",
                "provider_search: http_json execution json_body.[redacted] must be valid JSON",
                "provider_search: http_json execution json_body.filters[0].[redacted] must be valid JSON",
            ),
        )
        joined_diagnostics = "\n".join(diagnostics["invalid_tool_executions"])
        self.assertNotIn("api_key", joined_diagnostics)
        self.assertNotIn("access_token", joined_diagnostics)
        self.assertNotIn("client_secret", joined_diagnostics)

    def test_build_tool_registry_settings_execution_diagnostics_accept_http_json_query_params_root_template(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/search",
                                "query_params": "$params",
                                "result_fields": {
                                    "documents_total": "$.meta.total",
                                },
                            },
                        }
                    }
                ),
            )
        )

        self.assertEqual(diagnostics["invalid_tool_executions"], ())

    def test_build_tool_registry_settings_execution_diagnostics_reject_http_json_query_params_literal_string(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/search",
                                "query_params": "q=margin",
                                "result_fields": {
                                    "documents_total": "$.meta.total",
                                },
                            },
                        }
                    }
                ),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution query_params must be an object",
            ),
        )

    def test_build_tool_registry_settings_execution_diagnostics_accept_http_json_headers_root_template(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/search",
                                "headers": "$headers",
                                "result_fields": {
                                    "documents_total": "$.meta.total",
                                },
                            },
                        }
                    }
                ),
            )
        )

        self.assertEqual(diagnostics["invalid_tool_executions"], ())

    def test_build_tool_registry_settings_execution_diagnostics_reject_http_json_headers_literal_string(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/search",
                                "headers": "Authorization: Bearer token",
                                "result_fields": {
                                    "documents_total": "$.meta.total",
                                },
                            },
                        }
                    }
                ),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution headers must be an object",
            ),
        )

    def test_build_tool_registry_settings_execution_diagnostics_redacts_sensitive_missing_template_reference_paths(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/search",
                                "query_params": {
                                    "api_key": "$tool_registry_api_key_typo",
                                },
                                "json_body": {
                                    "access_token": "$settings_access_token_typo",
                                },
                            },
                        }
                    }
                ),
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution references unsupported runtime template variable [redacted] in query_params.[redacted]",
                "provider_search: http_json execution references unsupported runtime template variable [redacted] in json_body.[redacted]",
            ),
        )
        joined_diagnostics = "\n".join(diagnostics["invalid_tool_executions"])
        self.assertNotIn("tool_registry_api_key_typo", joined_diagnostics)
        self.assertNotIn("settings_access_token_typo", joined_diagnostics)
        self.assertNotIn("query_params.api_key", joined_diagnostics)
        self.assertNotIn("json_body.access_token", joined_diagnostics)

    def test_build_tool_registry_settings_execution_summary_redacts_http_json_url_path_sensitive_assignment(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/v1/token=hidden/search/api_key/secret-value",
                        },
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        self.assertEqual(
            extra_tools["provider_search"].execution_summary,
            {
                "method": "GET",
                "url_origin": "https://provider.example",
                "url_path": "/v1/[redacted]/search/[redacted]/[redacted]",
            },
        )
        self.assertNotIn(
            "token",
            json.dumps(extra_tools["provider_search"].execution_summary),
        )
        self.assertNotIn(
            "api_key",
            json.dumps(extra_tools["provider_search"].execution_summary),
        )
        self.assertNotIn(
            "hidden",
            json.dumps(extra_tools["provider_search"].execution_summary),
        )
        self.assertNotIn(
            "secret-value",
            json.dumps(extra_tools["provider_search"].execution_summary),
        )

    def test_build_tool_registry_settings_execution_summary_redacts_http_json_percent_encoded_sensitive_url_path(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/v1/api_key%2Fsecret-value/search",
                        },
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        self.assertEqual(
            extra_tools["provider_search"].execution_summary,
            {
                "method": "GET",
                "url_origin": "https://provider.example",
                "url_path": "/v1/[redacted]/[redacted]/search",
            },
        )
        summary_json = json.dumps(extra_tools["provider_search"].execution_summary)
        self.assertNotIn("api_key", summary_json)
        self.assertNotIn("secret-value", summary_json)

    def test_build_tool_registry_settings_execution_summary_redacts_http_json_sensitive_result_field_names(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "result_fields": {
                                "documents_total": "$.meta.total",
                                "access_token": "$.meta.token",
                                "api_key": "$.meta.api_key",
                            },
                        },
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        self.assertEqual(
            extra_tools["provider_search"].execution_summary,
            {
                "method": "GET",
                "url_origin": "https://provider.example",
                "url_path": "/search",
                "result_field_names": [
                    "documents_total",
                    "[redacted]",
                    "[redacted]",
                ],
            },
        )
        self.assertNotIn(
            "access_token",
            json.dumps(extra_tools["provider_search"].execution_summary),
        )
        self.assertNotIn(
            "api_key",
            json.dumps(extra_tools["provider_search"].execution_summary),
        )

    def test_build_tool_registry_settings_execution_summary_redacts_http_json_sensitive_response_path(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_search": {
                        "template": "task_retrieve",
                        "label": "Provider Search",
                        "kind": "provider_retrieval",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/search",
                            "response_path": "$.data.token=hidden",
                        },
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        self.assertEqual(
            extra_tools["provider_search"].execution_summary,
            {
                "method": "GET",
                "url_origin": "https://provider.example",
                "url_path": "/search",
                "response_path": "$.data.[redacted]",
            },
        )
        self.assertNotIn(
            "hidden",
            json.dumps(extra_tools["provider_search"].execution_summary),
        )
        self.assertNotIn(
            "token",
            json.dumps(extra_tools["provider_search"].execution_summary),
        )

    def test_build_tool_execution_summary_accepts_http_json_typed_request_values(
        self,
    ) -> None:
        class HeaderMapping:
            def model_dump(self) -> UserDict:
                return UserDict(
                    {
                        UserString("Content-Type"): "application/json",
                        "X-Provider": "typed-source",
                    }
                )

        class QueryMapping:
            def to_json(self) -> UserString:
                return UserString('{"source":"analytics","tag":["fresh","typed"]}')

        class BodyPayload:
            def to_dict(self) -> UserDict:
                return UserDict(
                    {
                        UserString("expression"): "1+2*3",
                        "filters": UserList(["provider", "fresh"]),
                    }
                )

        execution_summary = (
            tool_runtime_module._build_tool_execution_summary_from_spec(  # type: ignore[attr-defined]
                {
                    "kind": "http_json",
                    "url": "https://provider.example/search",
                    "method": "POST",
                    "headers": HeaderMapping(),
                    "query_params": QueryMapping(),
                    "json_body": BodyPayload(),
                    "response_path": UserString("$.data"),
                    "result_fields": UserDict(
                        {
                            UserString("result"): UserString("$.data.value"),
                        }
                    ),
                }
            )
        )

        self.assertEqual(
            execution_summary,
            {
                "method": "POST",
                "url_origin": "https://provider.example",
                "url_path": "/search",
                "header_count": 2,
                "query_param_count": 2,
                "json_body_field_count": 2,
                "response_path": "$.data",
                "result_field_names": ["result"],
            },
        )

    def test_build_tool_execution_summary_accepts_http_json_typed_template_result_fields(
        self,
    ) -> None:
        class ResultFields:
            def model_dump(self) -> UserDict:
                return UserDict(
                    {
                        UserString("documents_total"): UserString("$.meta.total"),
                        "request_id": UserString("$.meta.request_id"),
                    }
                )

        execution_summary = (
            tool_runtime_module._build_tool_execution_summary_from_spec(  # type: ignore[attr-defined]
                {
                    "kind": "http_json",
                    "url": "https://provider.example/search",
                    "result_fields": "$settings_model",
                },
                template_context={
                    "settings_model": ResultFields(),
                },
            )
        )

        self.assertEqual(
            execution_summary,
            {
                "method": "GET",
                "url_origin": "https://provider.example",
                "url_path": "/search",
                "result_field_names": ["documents_total", "request_id"],
            },
        )

    def test_build_tool_execution_summary_accepts_http_json_control_field_string_wrappers(
        self,
    ) -> None:
        execution_summary = (
            tool_runtime_module._build_tool_execution_summary_from_spec(  # type: ignore[attr-defined]
                {
                    "kind": UserString("http_json"),
                    "url": UserString("https://provider.example/search"),
                    "method": UserString("POST"),
                    "json_body": {
                        "query": "$query",
                    },
                }
            )
        )

        self.assertEqual(
            execution_summary,
            {
                "method": "POST",
                "url_origin": "https://provider.example",
                "url_path": "/search",
                "json_body_field_count": 1,
            },
        )

    def test_build_tool_execution_summary_accepts_http_json_kind_string_wrapper(
        self,
    ) -> None:
        execution_summary = (
            tool_runtime_module._build_tool_execution_summary_from_spec(  # type: ignore[attr-defined]
                {
                    "kind": UserString("http_json"),
                    "url": "https://provider.example/search",
                }
            )
        )

        self.assertEqual(
            execution_summary,
            {
                "method": "GET",
                "url_origin": "https://provider.example",
                "url_path": "/search",
            },
        )

    def test_build_tool_execution_summary_renders_http_json_method_template(
        self,
    ) -> None:
        execution_summary = (
            tool_runtime_module._build_tool_execution_summary_from_spec(  # type: ignore[attr-defined]
                {
                    "kind": "http_json",
                    "url": "https://provider.example/search",
                    "method": "$settings_mode",
                    "json_body": {
                        "query": "$query",
                    },
                },
                template_context={
                    "settings_mode": UserString("PATCH"),
                },
            )
        )

        self.assertEqual(
            execution_summary,
            {
                "method": "PATCH",
                "url_origin": "https://provider.example",
                "url_path": "/search",
                "json_body_field_count": 1,
            },
        )

    def test_build_tool_registry_extra_tools_from_settings_filters_sensitive_result_preview_and_output_keys(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_math": {
                        "template": "calc_eval",
                        "label": "Provider Math",
                        "kind": "provider_calc",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/calc",
                            "result_fields": {
                                "result": "$.data.value",
                                "access_token": "$.meta.token",
                                "api_key": "$.meta.api_key",
                            },
                        },
                        "result_preview_keys": ["result", "access_token"],
                        "result_output_keys": ["result", "api_key"],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        self.assertEqual(extra_tools["provider_math"].result_preview_keys, ("result",))
        self.assertEqual(extra_tools["provider_math"].result_output_keys, ("result",))

    def test_build_tool_registry_extra_tools_from_settings_does_not_fallback_when_only_sensitive_result_keys_are_declared(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_extra_tools_json=json.dumps(
                {
                    "provider_math": {
                        "template": "calc_eval",
                        "label": "Provider Math",
                        "kind": "provider_calc",
                        "execution": {
                            "kind": "http_json",
                            "url": "https://provider.example/calc",
                            "result_fields": {
                                "access_token": "$.meta.token",
                            },
                        },
                        "result_preview_keys": ["access_token"],
                        "result_output_keys": ["api_key"],
                    }
                }
            )
        )

        extra_tools = build_tool_registry_extra_tools_from_settings(settings=settings)

        self.assertEqual(extra_tools["provider_math"].result_preview_keys, ())
        self.assertEqual(extra_tools["provider_math"].result_output_keys, ())

    def test_build_tool_registry_settings_execution_diagnostics_reports_unsupported_runtime_template_variables(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/search",
                                "headers": {
                                    "Authorization": "Bearer ${settings_api_keey}",
                                },
                                "query_params": {
                                    "source": "$tool_registry_provider_sourcee",
                                    "q": "$query",
                                },
                            },
                        }
                    }
                )
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution references unsupported runtime template variable settings_api_keey in headers.Authorization",
                "provider_search: http_json execution references unsupported runtime template variable tool_registry_provider_sourcee in query_params.source",
            ),
        )

    def test_build_tool_registry_settings_execution_diagnostics_reports_invalid_result_field_paths(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/search",
                                "result_fields": {
                                    "documents_total": 123,
                                    "request_id": " ",
                                },
                            },
                        }
                    }
                )
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution result_fields.documents_total must be a non-empty string path",
                "provider_search: http_json execution result_fields.request_id must be a non-empty string path",
            ),
        )

    def test_build_tool_registry_settings_execution_diagnostics_redacts_sensitive_result_field_names(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/search",
                                "result_fields": {
                                    "access_token": 123,
                                    "api_key": "$.data.documents[-1]",
                                },
                            },
                        }
                    }
                )
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution result_fields.[redacted] must be a non-empty string path",
                "provider_search: http_json execution result_fields.[redacted] must use dot fields and numeric indexes",
            ),
        )
        joined_diagnostics = "\n".join(diagnostics["invalid_tool_executions"])
        self.assertNotIn("access_token", joined_diagnostics)
        self.assertNotIn("api_key", joined_diagnostics)

    def test_build_tool_registry_settings_execution_diagnostics_reports_blank_result_field_names(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/search",
                                "result_fields": {
                                    " ": "$.meta.total",
                                },
                            },
                        }
                    }
                )
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution result_fields must include at least one non-empty field name",
            ),
        )

    def test_build_tool_registry_settings_execution_diagnostics_reports_mixed_blank_result_field_names(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/search",
                                "result_fields": {
                                    " ": "$.meta.total",
                                    "documents_total": "$.meta.total",
                                },
                            },
                        }
                    }
                )
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution result_fields must not include blank field names",
            ),
        )

    def test_build_tool_registry_settings_execution_diagnostics_reports_empty_result_fields_mapping(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/search",
                                "result_fields": {},
                            },
                        }
                    }
                )
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution result_fields must include at least one field mapping",
            ),
        )

    def test_build_tool_registry_settings_execution_diagnostics_reports_blank_response_path(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/search",
                                "response_path": " ",
                            },
                        }
                    }
                )
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution response_path must be a non-empty string when provided",
            ),
        )

    def test_build_tool_registry_settings_execution_diagnostics_reports_blank_request_field_names(
        self,
    ) -> None:
        diagnostics = build_tool_registry_settings_execution_diagnostics(
            settings=SimpleNamespace(
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/search",
                                "headers": {
                                    " ": "Bearer demo",
                                },
                                "query_params": {
                                    " ": "$query",
                                },
                                "json_body": {
                                    " ": "$query",
                                },
                            },
                        }
                    }
                )
            )
        )

        self.assertEqual(
            diagnostics["invalid_tool_executions"],
            (
                "provider_search: http_json execution headers must not include blank field names",
                "provider_search: http_json execution headers must include at least one non-empty field name when provided",
                "provider_search: http_json execution query_params must not include blank field names",
                "provider_search: http_json execution query_params must include at least one non-empty field name when provided",
                "provider_search: http_json execution json_body must not include blank field names",
                "provider_search: http_json execution json_body must include at least one non-empty field name when provided",
            ),
        )

    def test_merge_tool_registry_file_diagnostics_accepts_list_values(self) -> None:
        diagnostics = tool_runtime_module._merge_tool_registry_file_diagnostics(  # type: ignore[attr-defined]
            {
                "skipped_registry_sources": ["planning_suite", "planning_suite"],
                "missing_registry_sources": [],
                "skipped_registry_files": ["/tmp/base.json"],
                "missing_registry_files": ["/tmp/missing.json"],
                "skipped_registry_dirs": [],
                "missing_registry_dirs": ["/tmp/missing-dir"],
            },
            {
                "skipped_registry_sources": ["planning_suite", "planning_suite_2"],
                "missing_registry_sources": [],
                "skipped_registry_files": [],
                "missing_registry_files": ["/tmp/missing.json", "/tmp/missing-2.json"],
                "skipped_registry_dirs": [],
                "missing_registry_dirs": [],
            },
        )

        self.assertEqual(
            diagnostics,
            {
                "skipped_registry_sources": ("planning_suite", "planning_suite_2"),
                "missing_registry_sources": (),
                "skipped_registry_files": ("/tmp/base.json",),
                "missing_registry_files": (
                    "/tmp/missing.json",
                    "/tmp/missing-2.json",
                ),
                "skipped_registry_dirs": (),
                "missing_registry_dirs": ("/tmp/missing-dir",),
                "invalid_tool_executions": (),
            },
        )

    def test_build_tool_registry_diagnostics_summary_accepts_list_values(self) -> None:
        diagnostics = {
            "skipped_registry_sources": ["planning_suite"],
            "missing_registry_sources": [],
            "skipped_registry_files": ["/tmp/base.json"],
            "missing_registry_files": ["/tmp/missing.json"],
            "skipped_registry_dirs": [],
            "missing_registry_dirs": ["/tmp/missing-dir"],
        }

        result = build_tool_registry_diagnostics_summary(diagnostics=diagnostics)

        self.assertTrue(result["has_diagnostics"])
        self.assertEqual(result["skipped_total"], 2)
        self.assertEqual(result["missing_total"], 2)
        self.assertEqual(result["total"], 4)
        self.assertEqual(
            result["entries"],
            (
                {
                    "kind": "skipped",
                    "target": "registry_sources",
                    "count": 1,
                    "values": ("planning_suite",),
                },
                {
                    "kind": "skipped",
                    "target": "registry_files",
                    "count": 1,
                    "values": ("/tmp/base.json",),
                },
                {
                    "kind": "missing",
                    "target": "registry_files",
                    "count": 1,
                    "values": ("/tmp/missing.json",),
                },
                {
                    "kind": "missing",
                    "target": "registry_dirs",
                    "count": 1,
                    "values": ("/tmp/missing-dir",),
                },
            ),
        )

    def test_build_tool_registry_diagnostics_summary_model_keeps_fields(self) -> None:
        diagnostics = {
            "skipped_registry_sources": ("planning_suite",),
            "missing_registry_sources": (),
            "skipped_registry_files": (),
            "missing_registry_files": ("/tmp/missing.json",),
            "skipped_registry_dirs": (),
            "missing_registry_dirs": (),
        }

        result = build_tool_registry_diagnostics_summary_model(diagnostics=diagnostics)

        self.assertTrue(result.has_diagnostics)
        self.assertEqual(result.skipped_total, 1)
        self.assertEqual(result.missing_total, 1)
        self.assertEqual(result.total, 2)
        self.assertEqual(result.entries[0]["kind"], "skipped")
        self.assertEqual(result.entries[1]["kind"], "missing")

    def test_build_tool_registry_diagnostics_runtime_artifacts_keep_shape(self) -> None:
        diagnostics = {
            "skipped_registry_sources": ("planning_suite",),
            "missing_registry_sources": (),
            "skipped_registry_files": (),
            "missing_registry_files": ("/tmp/missing.json",),
            "skipped_registry_dirs": (),
            "missing_registry_dirs": (),
        }

        result = build_tool_registry_diagnostics_runtime_artifacts(
            task_id="task-1",
            step_id="step-1",
            seq=4,
            model="mock-gpt",
            provider_source_name="file_source",
            diagnostics=diagnostics,
        )

        self.assertTrue(result["summary"]["has_diagnostics"])
        self.assertEqual(
            result["trace_step"],
            {
                "id": "step-1",
                "seq": 4,
                "type": "observation",
                "content": (
                    "Tool registry diagnostics: source=file_source skipped=1 missing=1\n"
                    "skipped registry sources: planning_suite\n"
                    "missing registry files: /tmp/missing.json"
                ),
                "meta": {
                    "model": "mock-gpt",
                    "step_type": "tool_registry_diagnostics",
                    "tokens": None,
                    "cost_estimate": None,
                    "tool_registry": {
                        "provider_source": "file_source",
                        "has_diagnostics": True,
                        "skipped_total": 1,
                        "missing_total": 1,
                        "total": 2,
                        "entries": (
                            {
                                "kind": "skipped",
                                "target": "registry_sources",
                                "count": 1,
                                "values": ("planning_suite",),
                            },
                            {
                                "kind": "missing",
                                "target": "registry_files",
                                "count": 1,
                                "values": ("/tmp/missing.json",),
                            },
                        ),
                    },
                },
            },
        )
        self.assertEqual(
            result["trace_event"],
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": result["trace_step"],
            },
        )
        self.assertEqual(
            result["audit_detail"],
            {
                "provider_source": "file_source",
                "has_diagnostics": True,
                "skipped_total": 1,
                "missing_total": 1,
                "total": 2,
                "entries": (
                    {
                        "kind": "skipped",
                        "target": "registry_sources",
                        "count": 1,
                        "values": ("planning_suite",),
                    },
                    {
                        "kind": "missing",
                        "target": "registry_files",
                        "count": 1,
                        "values": ("/tmp/missing.json",),
                    },
                ),
            },
        )

    def test_build_tool_registry_diagnostics_runtime_artifacts_redacts_sensitive_values(
        self,
    ) -> None:
        diagnostics = {
            "skipped_registry_sources": (),
            "missing_registry_sources": (),
            "skipped_registry_files": (),
            "missing_registry_files": (),
            "skipped_registry_dirs": (),
            "missing_registry_dirs": (),
            "invalid_tool_executions": (
                "provider_status: unsupported tool execution kind api_key=hidden",
                "provider_search: http_json execution query_params.access_token must be safe",
                "provider_search: http_json execution result_fields['access_token'] must be safe",
            ),
        }

        result = build_tool_registry_diagnostics_runtime_artifacts(
            task_id="task-1",
            step_id="step-1",
            seq=4,
            model="mock-gpt",
            provider_source_name="file_source",
            diagnostics=diagnostics,
        )

        self.assertTrue(result["summary"]["has_diagnostics"])
        self.assertEqual(
            result["summary"]["entries"][0]["values"],
            (
                "provider_status: unsupported tool execution kind [redacted]",
                "provider_search: http_json execution [redacted] must be safe",
                "provider_search: http_json execution [redacted] must be safe",
            ),
        )
        content = result["trace_step"]["content"]
        self.assertIn("unsupported tool execution kind [redacted]", content)
        self.assertIn("http_json execution [redacted] must be safe", content)
        self.assertNotIn("api_key=hidden", content)
        self.assertNotIn("access_token", content)
