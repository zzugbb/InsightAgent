from __future__ import annotations

from .context import *


class ProviderSourceHttpJsonMixinPart2:
    def test_http_json_provider_search_uses_esearchresult_count_and_idlist(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="",
                tool_registry_provider_sources_json=json.dumps({}),
                tool_registry_overrides_json=None,
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/pubmed/esearch",
                                "method": "GET",
                                "query_params": {"term": "$query"},
                            },
                            "runtime_semantic_kind": "provider_search",
                        }
                    }
                ),
            )
        )

        class FakeHttpResponse:
            def read(self) -> bytes:
                return json.dumps(
                    {
                        "header": {"type": "esearch"},
                        "esearchresult": {
                            "count": "123",
                            "retmax": "2",
                            "retstart": "0",
                            "idlist": ["31452104", "31437182"],
                        },
                    }
                ).encode("utf-8")

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = (  # type: ignore[attr-defined]
                lambda request, timeout=0: FakeHttpResponse()
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "pubmed total"},
                prompt="search",
                user_id="user-1",
                attempt=0,
                registry_provider=registry_provider,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(output["documents_total"], 123)
        self.assertEqual(output["hit_count"], 2)
        self.assertEqual(output["tool_kind"], "provider_search")

    def test_http_json_provider_search_uses_result_list_hit_count(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="",
                tool_registry_provider_sources_json=json.dumps({}),
                tool_registry_overrides_json=None,
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/europepmc/search",
                                "method": "GET",
                                "query_params": {"query": "$query"},
                            },
                            "runtime_semantic_kind": "provider_search",
                        }
                    }
                ),
            )
        )

        class FakeHttpResponse:
            def read(self) -> bytes:
                return json.dumps(
                    {
                        "version": "6.9",
                        "hitCount": "321",
                        "resultList": {
                            "result": [
                                {"title": "Alpha"},
                                {"title": "Beta"},
                            ]
                        },
                    }
                ).encode("utf-8")

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = (  # type: ignore[attr-defined]
                lambda request, timeout=0: FakeHttpResponse()
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "europe pmc total"},
                prompt="search",
                user_id="user-1",
                attempt=0,
                registry_provider=registry_provider,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(output["documents_total"], 321)
        self.assertEqual(output["hit_count"], 2)
        self.assertEqual(output["tool_kind"], "provider_search")

    def test_http_json_provider_search_uses_custom_search_total_results(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="",
                tool_registry_provider_sources_json=json.dumps({}),
                tool_registry_overrides_json=None,
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/google-custom-search",
                                "method": "GET",
                                "query_params": {"q": "$query"},
                            },
                            "runtime_semantic_kind": "provider_search",
                        }
                    }
                ),
            )
        )

        class FakeHttpResponse:
            def read(self) -> bytes:
                return json.dumps(
                    {
                        "kind": "customsearch#search",
                        "queries": {
                            "request": [
                                {"title": "Search", "totalResults": "123"}
                            ]
                        },
                        "items": [
                            {"title": "Alpha"},
                            {"title": "Beta"},
                        ],
                    }
                ).encode("utf-8")

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = (  # type: ignore[attr-defined]
                lambda request, timeout=0: FakeHttpResponse()
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "custom search total"},
                prompt="search",
                user_id="user-1",
                attempt=0,
                registry_provider=registry_provider,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(output["documents_total"], 123)
        self.assertEqual(output["hit_count"], 2)
        self.assertEqual(output["tool_kind"], "provider_search")

    def test_http_json_provider_search_uses_serper_organic_hits(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="",
                tool_registry_provider_sources_json=json.dumps({}),
                tool_registry_overrides_json=None,
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "provider_search": {
                            "template": "task_retrieve",
                            "label": "Provider Search",
                            "kind": "provider_retrieval",
                            "execution": {
                                "kind": "http_json",
                                "url": "https://provider.example/serper/search",
                                "method": "POST",
                                "body": {"q": "$query"},
                            },
                            "runtime_semantic_kind": "provider_search",
                        }
                    }
                ),
            )
        )

        class FakeHttpResponse:
            def read(self) -> bytes:
                return json.dumps(
                    {
                        "searchInformation": {
                            "totalResults": "456",
                            "timeTaken": 0.21,
                        },
                        "organic": [
                            {"title": "Alpha", "link": "https://example.test/a"},
                            {"title": "Beta", "link": "https://example.test/b"},
                        ],
                    }
                ).encode("utf-8")

            def __enter__(self) -> "FakeHttpResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        original_urlopen = getattr(tool_runtime_module, "urlopen", None)
        try:
            tool_runtime_module.urlopen = (  # type: ignore[attr-defined]
                lambda request, timeout=0: FakeHttpResponse()
            )

            output = run_tool(
                name="provider_search",
                tool_input={"query": "serper organic results"},
                prompt="search",
                user_id="user-1",
                attempt=0,
                registry_provider=registry_provider,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(output["documents_total"], 456)
        self.assertEqual(output["hit_count"], 2)
        self.assertEqual(output["tool_kind"], "provider_search")

    def test_named_loader_file_backed_source_uses_selected_source_profile_in_http_json_request(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "loader-registry.json"
            registry_file.write_text(
                json.dumps(
                    {
                        "extra_tools": {
                            "provider_search": {
                                "template": "task_retrieve",
                                "label": "Provider Search",
                                "kind": "provider_retrieval",
                                "execution": {
                                    "kind": "http_json",
                                    "url": "https://provider.example/search",
                                    "method": "POST",
                                    "headers": {
                                        "Authorization": "Bearer ${tool_registry_profile}",
                                        "X-Provider-Source": "$tool_registry_provider_source",
                                    },
                                    "query_params": {
                                        "query": "$query",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "json_body": {
                                        "query": "$query",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "documents_total": "$.total",
                                        "knowledge_base_id": "$.kb",
                                    },
                                },
                                "runtime_semantic_kind": "provider_search",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            registry_provider = get_configured_tool_registry_provider(
                settings=SimpleNamespace(
                    tool_registry_profile="default",
                    tool_registry_provider_source="search_suite",
                    tool_registry_loaders_json=json.dumps(
                        {
                            "search_loader": {
                                "registry_file": str(registry_file),
                            }
                        }
                    ),
                    tool_registry_provider_sources_json=json.dumps(
                        {
                            "search_suite": {
                                "loader": "search_loader",
                                "profile": "retrieval_only",
                            }
                        }
                    ),
                    tool_registry_overrides_json=None,
                    tool_registry_extra_tools_json=None,
                )
            )
            urlopen_calls: list[object] = []

            class FakeHttpResponse:
                def read(self) -> bytes:
                    return b'{"data":{"total":5,"kb":"loader-kb"}}'

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
                    tool_input={"query": "loader risk"},
                    prompt="search",
                    user_id="user-1",
                    attempt=0,
                    registry_provider=registry_provider,
                )
            finally:
                if original_urlopen is None:
                    delattr(tool_runtime_module, "urlopen")
                else:
                    tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(output["documents_total"], 5)
        self.assertEqual(output["knowledge_base_id"], "loader-kb")
        self.assertEqual(len(urlopen_calls), 1)
        parsed_query = parse_qs(urlparse(urlopen_calls[0].full_url).query)
        self.assertEqual(parsed_query["source"], ["search_suite"])
        self.assertEqual(parsed_query["profile"], ["retrieval_only"])
        request = urlopen_calls[0]
        self.assertEqual(request.headers["Authorization"], "Bearer retrieval_only")
        self.assertEqual(request.headers["X-provider-source"], "search_suite")
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {
                "query": "loader risk",
                "source": "search_suite",
                "profile": "retrieval_only",
            },
        )

    def test_named_loader_shorthand_with_profile_uses_selected_source_profile_in_http_json_request(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_profile="default",
                tool_registry_provider_source="search_suite",
                tool_registry_loaders_json=json.dumps(
                    {
                        "search_loader": {
                            "profile": "retrieval_only",
                            "provider_search": {
                                "template": "task_retrieve",
                                "label": "Provider Search",
                                "kind": "provider_retrieval",
                                "execution": {
                                    "kind": "http_json",
                                    "url": "https://provider.example/search",
                                    "method": "POST",
                                    "headers": {
                                        "Authorization": "Bearer ${tool_registry_profile}",
                                        "X-Provider-Source": "$tool_registry_provider_source",
                                    },
                                    "query_params": {
                                        "query": "$query",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "json_body": {
                                        "query": "$query",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "documents_total": "$.total",
                                        "knowledge_base_id": "$.kb",
                                    },
                                },
                                "runtime_semantic_kind": "provider_search",
                            },
                        }
                    }
                ),
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "search_suite": {
                            "loader": "search_loader",
                            "profile": "retrieval_only",
                        }
                    }
                ),
                tool_registry_overrides_json=None,
                tool_registry_extra_tools_json=None,
            )
        )
        urlopen_calls: list[object] = []

        class FakeHttpResponse:
            def read(self) -> bytes:
                return b'{"data":{"total":11,"kb":"loader-shorthand-kb"}}'

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
                tool_input={"query": "loader shorthand"},
                prompt="search",
                user_id="user-1",
                attempt=0,
                registry_provider=registry_provider,
            )
        finally:
            if original_urlopen is None:
                delattr(tool_runtime_module, "urlopen")
            else:
                tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(output["documents_total"], 11)
        self.assertEqual(output["knowledge_base_id"], "loader-shorthand-kb")
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        parsed_query = parse_qs(urlparse(request.full_url).query)
        self.assertEqual(parsed_query["query"], ["loader shorthand"])
        self.assertEqual(parsed_query["source"], ["search_suite"])
        self.assertEqual(parsed_query["profile"], ["retrieval_only"])
        self.assertEqual(request.headers["Authorization"], "Bearer retrieval_only")
        self.assertEqual(request.headers["X-provider-source"], "search_suite")
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {
                "query": "loader shorthand",
                "source": "search_suite",
                "profile": "retrieval_only",
            },
        )

    def test_named_provider_loader_file_backed_source_uses_selected_source_profile_in_http_json_request(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "provider-loader-registry.json"
            registry_file.write_text(
                json.dumps(
                    {
                        "extra_tools": {
                            "provider_search": {
                                "template": "task_retrieve",
                                "label": "Provider Search",
                                "kind": "provider_retrieval",
                                "execution": {
                                    "kind": "http_json",
                                    "url": "https://provider.example/search",
                                    "method": "POST",
                                    "headers": {
                                        "Authorization": "Bearer ${tool_registry_profile}",
                                        "X-Provider-Source": "$tool_registry_provider_source",
                                    },
                                    "query_params": {
                                        "query": "$query",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "json_body": {
                                        "query": "$query",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "documents_total": "$.total",
                                        "knowledge_base_id": "$.kb",
                                    },
                                },
                                "runtime_semantic_kind": "provider_search",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            registry_provider = get_configured_tool_registry_provider(
                settings=SimpleNamespace(
                    tool_registry_profile="default",
                    tool_registry_provider_source="search_suite",
                    tool_registry_loaders_json=json.dumps(
                        {
                            "search_loader": {
                                "registry_file": str(registry_file),
                            }
                        }
                    ),
                    tool_registry_providers_json=json.dumps(
                        {
                            "search_provider": {
                                "loader": "search_loader",
                            }
                        }
                    ),
                    tool_registry_provider_sources_json=json.dumps(
                        {
                            "search_suite": {
                                "provider": "search_provider",
                                "profile": "retrieval_only",
                            }
                        }
                    ),
                    tool_registry_overrides_json=None,
                    tool_registry_extra_tools_json=None,
                )
            )
            urlopen_calls: list[object] = []

            class FakeHttpResponse:
                def read(self) -> bytes:
                    return b'{"data":{"total":6,"kb":"provider-loader-kb"}}'

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
                    tool_input={"query": "loader chain"},
                    prompt="search",
                    user_id="user-1",
                    attempt=0,
                    registry_provider=registry_provider,
                )
            finally:
                if original_urlopen is None:
                    delattr(tool_runtime_module, "urlopen")
                else:
                    tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(output["documents_total"], 6)
        self.assertEqual(output["knowledge_base_id"], "provider-loader-kb")
        self.assertEqual(len(urlopen_calls), 1)
        parsed_query = parse_qs(urlparse(urlopen_calls[0].full_url).query)
        self.assertEqual(parsed_query["source"], ["search_suite"])
        self.assertEqual(parsed_query["profile"], ["retrieval_only"])
        request = urlopen_calls[0]
        self.assertEqual(request.headers["Authorization"], "Bearer retrieval_only")
        self.assertEqual(request.headers["X-provider-source"], "search_suite")
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {
                "query": "loader chain",
                "source": "search_suite",
                "profile": "retrieval_only",
            },
        )

    def test_loader_factory_file_backed_source_uses_selected_source_profile_in_http_json_request(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "loader-factory-registry.json"
            registry_file.write_text(
                json.dumps(
                    {
                        "extra_tools": {
                            "provider_search": {
                                "template": "task_retrieve",
                                "label": "Provider Search",
                                "kind": "provider_retrieval",
                                "execution": {
                                    "kind": "http_json",
                                    "url": "https://provider.example/search",
                                    "method": "POST",
                                    "headers": {
                                        "Authorization": "Bearer ${tool_registry_profile}",
                                        "X-Provider-Source": "$tool_registry_provider_source",
                                    },
                                    "query_params": {
                                        "query": "$query",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "json_body": {
                                        "query": "$query",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "documents_total": "$.total",
                                        "knowledge_base_id": "$.kb",
                                    },
                                },
                                "runtime_semantic_kind": "provider_search",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            registry_provider = get_configured_tool_registry_provider(
                settings=SimpleNamespace(
                    tool_registry_profile="default",
                    tool_registry_provider_source="search_suite",
                    tool_registry_loader_factories_json=json.dumps(
                        {
                            "search_loader_factory": {
                                "registry_file": str(registry_file),
                            }
                        }
                    ),
                    tool_registry_provider_sources_json=json.dumps(
                        {
                            "search_suite": {
                                "loader_factory": "search_loader_factory",
                                "profile": "retrieval_only",
                            }
                        }
                    ),
                    tool_registry_overrides_json=None,
                    tool_registry_extra_tools_json=None,
                )
            )
            urlopen_calls: list[object] = []

            class FakeHttpResponse:
                def read(self) -> bytes:
                    return b'{"data":{"total":7,"kb":"loader-factory-kb"}}'

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
                    tool_input={"query": "factory risk"},
                    prompt="search",
                    user_id="user-1",
                    attempt=0,
                    registry_provider=registry_provider,
                )
            finally:
                if original_urlopen is None:
                    delattr(tool_runtime_module, "urlopen")
                else:
                    tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(output["documents_total"], 7)
        self.assertEqual(output["knowledge_base_id"], "loader-factory-kb")
        self.assertEqual(len(urlopen_calls), 1)
        parsed_query = parse_qs(urlparse(urlopen_calls[0].full_url).query)
        self.assertEqual(parsed_query["source"], ["search_suite"])
        self.assertEqual(parsed_query["profile"], ["retrieval_only"])
        request = urlopen_calls[0]
        self.assertEqual(request.headers["Authorization"], "Bearer retrieval_only")
        self.assertEqual(request.headers["X-provider-source"], "search_suite")
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {
                "query": "factory risk",
                "source": "search_suite",
                "profile": "retrieval_only",
            },
        )

    def test_loader_factory_file_backed_source_applies_factory_overrides_to_http_json_request(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "loader-factory-override-registry.json"
            registry_file.write_text(
                json.dumps(
                    {
                        "extra_tools": {
                            "provider_search": {
                                "template": "task_retrieve",
                                "label": "Provider Search",
                                "kind": "provider_retrieval",
                                "execution": {
                                    "kind": "http_json",
                                    "url": "https://provider.example/base-search",
                                    "method": "GET",
                                    "headers": {
                                        "X-Mode": "base",
                                        "X-Provider-Source": "$tool_registry_provider_source",
                                    },
                                    "query_params": {
                                        "q": "$query",
                                        "mode": "base",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "documents_total": "$.total",
                                        "knowledge_base_id": "$.kb",
                                    },
                                },
                                "runtime_semantic_kind": "provider_search",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            registry_provider = get_configured_tool_registry_provider(
                settings=SimpleNamespace(
                    tool_registry_profile="default",
                    tool_registry_provider_source="search_suite",
                    tool_registry_loader_factories_json=json.dumps(
                        {
                            "search_factory": {
                                "registry_file": str(registry_file),
                                "overrides": {
                                    "provider_search": {
                                        "label": "Factory Override Search",
                                        "execution": {
                                            "kind": "http_json",
                                            "url": "https://provider.example/factory-search",
                                            "method": "GET",
                                            "headers": {
                                                "X-Mode": "factory",
                                                "X-Provider-Source": "$tool_registry_provider_source",
                                                "X-Profile": "$tool_registry_profile",
                                            },
                                            "query_params": {
                                                "q": "$query",
                                                "mode": "factory",
                                                "source": "$tool_registry_provider_source",
                                                "profile": "$tool_registry_profile",
                                            },
                                            "response_path": "$.payload",
                                            "result_fields": {
                                                "documents_total": "$.count",
                                                "knowledge_base_id": "$.kb",
                                            },
                                        },
                                        "result_preview_keys": [
                                            "documents_total",
                                            "knowledge_base_id",
                                        ],
                                        "result_output_keys": [
                                            "documents_total",
                                            "knowledge_base_id",
                                        ],
                                        "runtime_semantic_kind": "provider_search",
                                    }
                                },
                            }
                        }
                    ),
                    tool_registry_provider_sources_json=json.dumps(
                        {
                            "search_suite": {
                                "loader_factory": "search_factory",
                                "profile": "retrieval_only",
                            }
                        }
                    ),
                    tool_registry_overrides_json=None,
                    tool_registry_extra_tools_json=None,
                )
            )
            urlopen_calls: list[object] = []

            class FakeHttpResponse:
                def read(self) -> bytes:
                    return b'{"payload":{"count":13,"kb":"factory-kb"}}'

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
                    tool_input={"query": "factory override"},
                    prompt="search",
                    user_id="user-1",
                    attempt=0,
                    registry_provider=registry_provider,
                )
            finally:
                if original_urlopen is None:
                    delattr(tool_runtime_module, "urlopen")
                else:
                    tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(
            output,
            {
                "documents_total": 13,
                "knowledge_base_id": "factory-kb",
                "tool_kind": "provider_search",
            },
        )
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        self.assertEqual(
            request.full_url,
            (
                "https://provider.example/factory-search?"
                "q=factory+override&mode=factory&source=search_suite"
                "&profile=retrieval_only"
            ),
        )
        self.assertEqual(request.headers["X-mode"], "factory")
        self.assertEqual(request.headers["X-provider-source"], "search_suite")
        self.assertEqual(request.headers["X-profile"], "retrieval_only")

    def test_loader_factory_alias_file_backed_source_applies_outer_factory_overrides_to_http_json_request(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "loader-factory-alias-registry.json"
            registry_file.write_text(
                json.dumps(
                    {
                        "extra_tools": {
                            "provider_search": {
                                "template": "task_retrieve",
                                "label": "Provider Search",
                                "kind": "provider_retrieval",
                                "execution": {
                                    "kind": "http_json",
                                    "url": "https://provider.example/base-search",
                                    "method": "GET",
                                    "headers": {
                                        "X-Mode": "base",
                                        "X-Provider-Source": "$tool_registry_provider_source",
                                    },
                                    "query_params": {
                                        "q": "$query",
                                        "mode": "base",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "documents_total": "$.total",
                                        "knowledge_base_id": "$.kb",
                                    },
                                },
                                "runtime_semantic_kind": "provider_search",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            registry_provider = get_configured_tool_registry_provider(
                settings=SimpleNamespace(
                    tool_registry_profile="default",
                    tool_registry_provider_source="search_suite",
                    tool_registry_loader_factories_json=json.dumps(
                        {
                            "outer_search_factory": {
                                "factory": "inner_search_factory",
                                "overrides": {
                                    "provider_search": {
                                        "label": "Outer Factory Search",
                                        "execution": {
                                            "kind": "http_json",
                                            "url": "https://provider.example/outer-factory-search",
                                            "method": "GET",
                                            "headers": {
                                                "X-Mode": "outer-factory",
                                                "X-Provider-Source": "$tool_registry_provider_source",
                                                "X-Profile": "$tool_registry_profile",
                                            },
                                            "query_params": {
                                                "q": "$query",
                                                "mode": "outer-factory",
                                                "source": "$tool_registry_provider_source",
                                                "profile": "$tool_registry_profile",
                                            },
                                            "response_path": "$.payload",
                                            "result_fields": {
                                                "documents_total": "$.count",
                                                "knowledge_base_id": "$.kb",
                                            },
                                        },
                                        "result_preview_keys": [
                                            "documents_total",
                                            "knowledge_base_id",
                                        ],
                                        "result_output_keys": [
                                            "documents_total",
                                            "knowledge_base_id",
                                        ],
                                        "runtime_semantic_kind": "provider_search",
                                    }
                                },
                            },
                            "inner_search_factory": {
                                "registry_file": str(registry_file),
                            },
                        }
                    ),
                    tool_registry_provider_sources_json=json.dumps(
                        {
                            "search_suite": {
                                "loader_factory": "outer_search_factory",
                                "profile": "retrieval_only",
                            }
                        }
                    ),
                    tool_registry_overrides_json=None,
                    tool_registry_extra_tools_json=None,
                )
            )
            urlopen_calls: list[object] = []

            class FakeHttpResponse:
                def read(self) -> bytes:
                    return b'{"payload":{"count":15,"kb":"outer-factory-kb"}}'

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
                    tool_input={"query": "factory alias override"},
                    prompt="search",
                    user_id="user-1",
                    attempt=0,
                    registry_provider=registry_provider,
                )
            finally:
                if original_urlopen is None:
                    delattr(tool_runtime_module, "urlopen")
                else:
                    tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(
            output,
            {
                "documents_total": 15,
                "knowledge_base_id": "outer-factory-kb",
                "tool_kind": "provider_search",
            },
        )
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        self.assertEqual(
            request.full_url,
            (
                "https://provider.example/outer-factory-search?"
                "q=factory+alias+override&mode=outer-factory"
                "&source=search_suite&profile=retrieval_only"
            ),
        )
        self.assertEqual(request.headers["X-mode"], "outer-factory")
        self.assertEqual(request.headers["X-provider-source"], "search_suite")
        self.assertEqual(request.headers["X-profile"], "retrieval_only")

    def test_provider_factory_file_backed_source_uses_selected_source_profile_in_http_json_request(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "provider-factory-registry.json"
            registry_file.write_text(
                json.dumps(
                    {
                        "extra_tools": {
                            "provider_search": {
                                "template": "task_retrieve",
                                "label": "Provider Search",
                                "kind": "provider_retrieval",
                                "execution": {
                                    "kind": "http_json",
                                    "url": "https://provider.example/search",
                                    "method": "POST",
                                    "headers": {
                                        "Authorization": "Bearer ${tool_registry_profile}",
                                        "X-Provider-Source": "$tool_registry_provider_source",
                                    },
                                    "query_params": {
                                        "query": "$query",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "json_body": {
                                        "query": "$query",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "documents_total": "$.total",
                                        "knowledge_base_id": "$.kb",
                                    },
                                },
                                "runtime_semantic_kind": "provider_search",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            registry_provider = get_configured_tool_registry_provider(
                settings=SimpleNamespace(
                    tool_registry_profile="default",
                    tool_registry_provider_source="search_suite",
                    tool_registry_provider_factories_json=json.dumps(
                        {
                            "search_provider_factory": {
                                "registry_file": str(registry_file),
                            }
                        }
                    ),
                    tool_registry_provider_sources_json=json.dumps(
                        {
                            "search_suite": {
                                "provider_factory": "search_provider_factory",
                                "profile": "retrieval_only",
                            }
                        }
                    ),
                    tool_registry_overrides_json=None,
                    tool_registry_extra_tools_json=None,
                )
            )
            urlopen_calls: list[object] = []

            class FakeHttpResponse:
                def read(self) -> bytes:
                    return b'{"data":{"total":8,"kb":"provider-factory-kb"}}'

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
                    tool_input={"query": "provider factory"},
                    prompt="search",
                    user_id="user-1",
                    attempt=0,
                    registry_provider=registry_provider,
                )
            finally:
                if original_urlopen is None:
                    delattr(tool_runtime_module, "urlopen")
                else:
                    tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(output["documents_total"], 8)
        self.assertEqual(output["knowledge_base_id"], "provider-factory-kb")
        self.assertEqual(len(urlopen_calls), 1)
        parsed_query = parse_qs(urlparse(urlopen_calls[0].full_url).query)
        self.assertEqual(parsed_query["source"], ["search_suite"])
        self.assertEqual(parsed_query["profile"], ["retrieval_only"])
        request = urlopen_calls[0]
        self.assertEqual(request.headers["Authorization"], "Bearer retrieval_only")
        self.assertEqual(request.headers["X-provider-source"], "search_suite")
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {
                "query": "provider factory",
                "source": "search_suite",
                "profile": "retrieval_only",
            },
        )

    def test_provider_factory_file_backed_source_applies_factory_overrides_to_http_json_request(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "provider-factory-override-registry.json"
            registry_file.write_text(
                json.dumps(
                    {
                        "extra_tools": {
                            "provider_search": {
                                "template": "task_retrieve",
                                "label": "Provider Search",
                                "kind": "provider_retrieval",
                                "execution": {
                                    "kind": "http_json",
                                    "url": "https://provider.example/base-provider-search",
                                    "method": "GET",
                                    "headers": {
                                        "X-Mode": "base",
                                        "X-Provider-Source": "$tool_registry_provider_source",
                                    },
                                    "query_params": {
                                        "q": "$query",
                                        "mode": "base",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "documents_total": "$.total",
                                        "knowledge_base_id": "$.kb",
                                    },
                                },
                                "runtime_semantic_kind": "provider_search",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            registry_provider = get_configured_tool_registry_provider(
                settings=SimpleNamespace(
                    tool_registry_profile="default",
                    tool_registry_provider_source="search_suite",
                    tool_registry_provider_factories_json=json.dumps(
                        {
                            "search_factory": {
                                "registry_file": str(registry_file),
                                "overrides": {
                                    "provider_search": {
                                        "label": "Provider Factory Override Search",
                                        "execution": {
                                            "kind": "http_json",
                                            "url": "https://provider.example/provider-factory-search",
                                            "method": "GET",
                                            "headers": {
                                                "X-Mode": "provider-factory",
                                                "X-Provider-Source": "$tool_registry_provider_source",
                                                "X-Profile": "$tool_registry_profile",
                                            },
                                            "query_params": {
                                                "q": "$query",
                                                "mode": "provider-factory",
                                                "source": "$tool_registry_provider_source",
                                                "profile": "$tool_registry_profile",
                                            },
                                            "response_path": "$.payload",
                                            "result_fields": {
                                                "documents_total": "$.count",
                                                "knowledge_base_id": "$.kb",
                                            },
                                        },
                                        "result_preview_keys": [
                                            "documents_total",
                                            "knowledge_base_id",
                                        ],
                                        "result_output_keys": [
                                            "documents_total",
                                            "knowledge_base_id",
                                        ],
                                        "runtime_semantic_kind": "provider_search",
                                    }
                                },
                            }
                        }
                    ),
                    tool_registry_provider_sources_json=json.dumps(
                        {
                            "search_suite": {
                                "provider_factory": "search_factory",
                                "profile": "retrieval_only",
                            }
                        }
                    ),
                    tool_registry_overrides_json=None,
                    tool_registry_extra_tools_json=None,
                )
            )
            urlopen_calls: list[object] = []

            class FakeHttpResponse:
                def read(self) -> bytes:
                    return b'{"payload":{"count":14,"kb":"provider-factory-kb"}}'

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
                    tool_input={"query": "provider factory override"},
                    prompt="search",
                    user_id="user-1",
                    attempt=0,
                    registry_provider=registry_provider,
                )
            finally:
                if original_urlopen is None:
                    delattr(tool_runtime_module, "urlopen")
                else:
                    tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(
            output,
            {
                "documents_total": 14,
                "knowledge_base_id": "provider-factory-kb",
                "tool_kind": "provider_search",
            },
        )
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        self.assertEqual(
            request.full_url,
            (
                "https://provider.example/provider-factory-search?"
                "q=provider+factory+override&mode=provider-factory"
                "&source=search_suite&profile=retrieval_only"
            ),
        )
        self.assertEqual(request.headers["X-mode"], "provider-factory")
        self.assertEqual(request.headers["X-provider-source"], "search_suite")
        self.assertEqual(request.headers["X-profile"], "retrieval_only")

    def test_provider_factory_alias_file_backed_source_applies_outer_factory_overrides_to_http_json_request(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "provider-factory-alias-registry.json"
            registry_file.write_text(
                json.dumps(
                    {
                        "extra_tools": {
                            "provider_search": {
                                "template": "task_retrieve",
                                "label": "Provider Search",
                                "kind": "provider_retrieval",
                                "execution": {
                                    "kind": "http_json",
                                    "url": "https://provider.example/base-provider-search",
                                    "method": "GET",
                                    "headers": {
                                        "X-Mode": "base",
                                        "X-Provider-Source": "$tool_registry_provider_source",
                                    },
                                    "query_params": {
                                        "q": "$query",
                                        "mode": "base",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "documents_total": "$.total",
                                        "knowledge_base_id": "$.kb",
                                    },
                                },
                                "runtime_semantic_kind": "provider_search",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            registry_provider = get_configured_tool_registry_provider(
                settings=SimpleNamespace(
                    tool_registry_profile="default",
                    tool_registry_provider_source="search_suite",
                    tool_registry_provider_factories_json=json.dumps(
                        {
                            "outer_search_factory": {
                                "factory": "inner_search_factory",
                                "overrides": {
                                    "provider_search": {
                                        "label": "Outer Provider Factory Search",
                                        "execution": {
                                            "kind": "http_json",
                                            "url": "https://provider.example/outer-provider-factory-search",
                                            "method": "GET",
                                            "headers": {
                                                "X-Mode": "outer-provider-factory",
                                                "X-Provider-Source": "$tool_registry_provider_source",
                                                "X-Profile": "$tool_registry_profile",
                                            },
                                            "query_params": {
                                                "q": "$query",
                                                "mode": "outer-provider-factory",
                                                "source": "$tool_registry_provider_source",
                                                "profile": "$tool_registry_profile",
                                            },
                                            "response_path": "$.payload",
                                            "result_fields": {
                                                "documents_total": "$.count",
                                                "knowledge_base_id": "$.kb",
                                            },
                                        },
                                        "result_preview_keys": [
                                            "documents_total",
                                            "knowledge_base_id",
                                        ],
                                        "result_output_keys": [
                                            "documents_total",
                                            "knowledge_base_id",
                                        ],
                                        "runtime_semantic_kind": "provider_search",
                                    }
                                },
                            },
                            "inner_search_factory": {
                                "registry_file": str(registry_file),
                            },
                        }
                    ),
                    tool_registry_provider_sources_json=json.dumps(
                        {
                            "search_suite": {
                                "provider_factory": "outer_search_factory",
                                "profile": "retrieval_only",
                            }
                        }
                    ),
                    tool_registry_overrides_json=None,
                    tool_registry_extra_tools_json=None,
                )
            )
            urlopen_calls: list[object] = []

            class FakeHttpResponse:
                def read(self) -> bytes:
                    return b'{"payload":{"count":16,"kb":"outer-provider-factory-kb"}}'

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
                    tool_input={"query": "provider factory alias override"},
                    prompt="search",
                    user_id="user-1",
                    attempt=0,
                    registry_provider=registry_provider,
                )
            finally:
                if original_urlopen is None:
                    delattr(tool_runtime_module, "urlopen")
                else:
                    tool_runtime_module.urlopen = original_urlopen  # type: ignore[attr-defined]

        self.assertEqual(
            output,
            {
                "documents_total": 16,
                "knowledge_base_id": "outer-provider-factory-kb",
                "tool_kind": "provider_search",
            },
        )
        self.assertEqual(len(urlopen_calls), 1)
        request = urlopen_calls[0]
        self.assertEqual(
            request.full_url,
            (
                "https://provider.example/outer-provider-factory-search?"
                "q=provider+factory+alias+override&mode=outer-provider-factory"
                "&source=search_suite&profile=retrieval_only"
            ),
        )
        self.assertEqual(request.headers["X-mode"], "outer-provider-factory")
        self.assertEqual(request.headers["X-provider-source"], "search_suite")
        self.assertEqual(request.headers["X-profile"], "retrieval_only")

    def test_named_loader_file_backed_source_preflight_summary_uses_selected_source_profile(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "loader-summary-registry.json"
            registry_file.write_text(
                json.dumps(
                    {
                        "extra_tools": {
                            "provider_search": {
                                "template": "task_retrieve",
                                "label": "Provider Search",
                                "kind": "provider_retrieval",
                                "execution": {
                                    "kind": "http_json",
                                    "url": "https://provider.example/${tool_registry_profile}/search",
                                    "method": "POST",
                                    "headers": {
                                        "Authorization": "Bearer ${tool_registry_profile}",
                                        "X-Provider-Source": "$tool_registry_provider_source",
                                    },
                                    "query_params": {
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "json_body": {
                                        "query": "$query",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "documents_total": "$.total",
                                        "request_id": "$.request_id",
                                    },
                                },
                                "runtime_semantic_kind": "provider_search",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            registry_provider = get_configured_tool_registry_provider(
                settings=SimpleNamespace(
                    tool_registry_profile="default",
                    tool_registry_provider_source="search_suite",
                    tool_registry_loaders_json=json.dumps(
                        {
                            "search_loader": {
                                "registry_file": str(registry_file),
                            }
                        }
                    ),
                    tool_registry_provider_sources_json=json.dumps(
                        {
                            "search_suite": {
                                "loader": "search_loader",
                                "profile": "retrieval_only",
                            }
                        }
                    ),
                    tool_registry_overrides_json=None,
                    tool_registry_extra_tools_json=None,
                )
            )

        provider_search_detail = next(
            detail
            for detail in build_configured_tool_registry_provider_preflight_tool_details(
                provider=registry_provider
            )
            if detail["name"] == "provider_search"
        )

        self.assertEqual(
            provider_search_detail["execution_summary"],
            {
                "method": "POST",
                "url_origin": "https://provider.example",
                "url_path": "/retrieval_only/search",
                "header_count": 2,
                "query_param_count": 2,
                "json_body_field_count": 3,
                "response_path": "$.data",
                "result_field_names": ["documents_total", "request_id"],
            },
        )

    def test_loader_factory_file_backed_source_preflight_summary_uses_selected_source_profile(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "loader-factory-summary-registry.json"
            registry_file.write_text(
                json.dumps(
                    {
                        "extra_tools": {
                            "provider_search": {
                                "template": "task_retrieve",
                                "label": "Provider Search",
                                "kind": "provider_retrieval",
                                "execution": {
                                    "kind": "http_json",
                                    "url": "https://provider.example/${tool_registry_profile}/search",
                                    "method": "POST",
                                    "headers": {
                                        "Authorization": "Bearer ${tool_registry_profile}",
                                        "X-Provider-Source": "$tool_registry_provider_source",
                                    },
                                    "query_params": {
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "json_body": {
                                        "query": "$query",
                                        "source": "$tool_registry_provider_source",
                                        "profile": "$tool_registry_profile",
                                    },
                                    "response_path": "$.data",
                                    "result_fields": {
                                        "documents_total": "$.total",
                                        "request_id": "$.request_id",
                                    },
                                },
                                "runtime_semantic_kind": "provider_search",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            registry_provider = get_configured_tool_registry_provider(
                settings=SimpleNamespace(
                    tool_registry_profile="default",
                    tool_registry_provider_source="search_suite",
                    tool_registry_loader_factories_json=json.dumps(
                        {
                            "search_loader_factory": {
                                "registry_file": str(registry_file),
                            }
                        }
                    ),
                    tool_registry_provider_sources_json=json.dumps(
                        {
                            "search_suite": {
                                "loader_factory": "search_loader_factory",
                                "profile": "retrieval_only",
                            }
                        }
                    ),
                    tool_registry_overrides_json=None,
                    tool_registry_extra_tools_json=None,
                )
            )

        provider_search_detail = next(
            detail
            for detail in build_configured_tool_registry_provider_preflight_tool_details(
                provider=registry_provider
            )
            if detail["name"] == "provider_search"
        )

        self.assertEqual(
            provider_search_detail["execution_summary"],
            {
                "method": "POST",
                "url_origin": "https://provider.example",
                "url_path": "/retrieval_only/search",
                "header_count": 2,
                "query_param_count": 2,
                "json_body_field_count": 3,
                "response_path": "$.data",
                "result_field_names": ["documents_total", "request_id"],
            },
        )
