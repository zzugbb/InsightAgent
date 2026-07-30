from __future__ import annotations

from .context import *


class RuntimeResultRagMixin:
    def test_build_tool_registry_providers_from_settings_supports_provider_factory_shape(self) -> None:
        settings = SimpleNamespace(
            tool_registry_providers_json=json.dumps(
                {
                    "planning_provider": {
                        "provider_factory": "planning_only",
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

    def test_build_tool_registry_providers_from_settings_reuses_shared_profile_name_helper_for_factory_hint(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_providers_json=json.dumps(
                {
                    "planning_provider": {
                        "provider_factory": "custom_factory",
                    }
                }
            )
        )
        original_get_tool_registry_profile_name_from_settings = (
            tool_runtime_module.get_tool_registry_profile_name_from_settings
        )
        original_build_tool_registry_provider_factories_from_settings = (
            tool_runtime_module.build_tool_registry_provider_factories_from_settings
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

            def fake_build_tool_registry_provider_factories_from_settings(*, settings=None):
                def factory(_settings=None):
                    return tool_runtime_module.get_default_tool_registry_provider()

                setattr(factory, "_tool_registry_profile_name", " Planning_Only ")
                return {"custom_factory": factory}

            tool_runtime_module.get_tool_registry_profile_name_from_settings = (
                fake_get_tool_registry_profile_name_from_settings
            )
            tool_runtime_module.build_tool_registry_provider_factories_from_settings = (
                fake_build_tool_registry_provider_factories_from_settings
            )
            providers = build_tool_registry_providers_from_settings(settings=settings)
        finally:
            tool_runtime_module.get_tool_registry_profile_name_from_settings = (
                original_get_tool_registry_profile_name_from_settings
            )
            tool_runtime_module.build_tool_registry_provider_factories_from_settings = (
                original_build_tool_registry_provider_factories_from_settings
            )

        self.assertEqual(tuple(sorted(providers)), ("planning_provider",))
        self.assertIn(" Planning_Only ", captured)
        self.assertEqual(
            get_registered_tool_names(registry_provider=providers["planning_provider"]),
            ("calc_eval",),
        )

    def test_build_tool_registry_loaders_from_settings_accepts_named_loader_factory_reference(self) -> None:
        settings = SimpleNamespace(
            tool_registry_loader_factories_json=json.dumps(
                {
                    "planning_factory": {
                        "factory": "planning_only",
                    }
                }
            ),
            tool_registry_loaders_json=json.dumps(
                {
                    "planning_loader": {
                        "loader_factory": "planning_factory",
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

        self.assertEqual(tuple(sorted(planning_registry)), ("calc_eval", "calc_eval_fast", "task_plan"))
        self.assertEqual(planning_registry["calc_eval"].label, "Planning Calculator")

    def test_build_tool_registry_loaders_from_settings_reuse_shared_reference_normalizer_for_loader_factory_reference(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_loader_factories_json=json.dumps(
                {
                    "planning_factory_shadow": {
                        "factory": "planning_only",
                    }
                }
            ),
            tool_registry_loaders_json=json.dumps(
                {
                    "planning_loader": {
                        "loader_factory": " Planning_Factory ",
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
            ),
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
            loaders = build_tool_registry_loaders_from_settings(settings=settings)
            planning_registry = loaders["planning_loader"]()
        finally:
            tool_runtime_module._normalize_named_tool_registry_component_name = (
                original_normalize_named_tool_registry_component_name
            )

        self.assertIn(" Planning_Factory ", captured)
        self.assertEqual(tuple(sorted(loaders)), ("planning_loader",))
        self.assertEqual(
            tuple(sorted(planning_registry)),
            ("calc_eval", "calc_eval_fast", "task_plan"),
        )
        self.assertEqual(planning_registry["calc_eval"].label, "Planning Calculator")

    def test_build_tool_registry_providers_from_settings_accepts_named_provider_factory_reference(self) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_factories_json=json.dumps(
                {
                    "planning_factory": {
                        "factory": "planning_only",
                    }
                }
            ),
            tool_registry_providers_json=json.dumps(
                {
                    "planning_provider": {
                        "provider_factory": "planning_factory",
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

    def test_build_tool_registry_providers_from_settings_reuse_shared_reference_normalizer_for_named_loader_reference(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_loaders_json=json.dumps(
                {
                    "planning_loader_shadow": {
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
            tool_registry_providers_json=json.dumps(
                {
                    "planning_provider": {
                        "loader": " Planning_Loader ",
                        "disabled_tool_names": ["mock_plan"],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                }
            ),
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
                if name == " Planning_Loader ":
                    return "planning_loader_shadow"
                if not isinstance(name, str):
                    return None
                normalized = name.strip().lower()
                return normalized or None

            tool_runtime_module._normalize_named_tool_registry_component_name = (
                fake_normalize_named_tool_registry_component_name
            )
            providers = build_tool_registry_providers_from_settings(settings=settings)
        finally:
            tool_runtime_module._normalize_named_tool_registry_component_name = (
                original_normalize_named_tool_registry_component_name
            )

        self.assertIn(" Planning_Loader ", captured)
        self.assertEqual(tuple(sorted(providers)), ("planning_provider",))
        self.assertEqual(
            get_registered_tool_names(registry_provider=providers["planning_provider"]),
            ("calc_eval", "calc_eval_fast"),
        )
        self.assertEqual(
            providers["planning_provider"].load_tool_registry()["calc_eval"].label,
            "Planning Calculator",
        )

    def test_build_tool_registry_loaders_from_settings_accepts_registry_file_shape(self) -> None:
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
                tool_registry_loaders_json=json.dumps(
                    {
                        "file_loader": {
                            "registry_file": str(registry_file),
                            "extra_tools": {
                                "mock_plan_brief": {
                                    "template": "mock_plan",
                                    "label": "Brief Planner",
                                }
                            },
                        }
                    }
                )
            )

            loaders = build_tool_registry_loaders_from_settings(settings=settings)
            file_registry = loaders["file_loader"]()

        self.assertEqual(tuple(sorted(loaders)), ("file_loader",))
        self.assertEqual(
            tuple(sorted(file_registry)),
            ("calc_eval_fast", "mock_plan_brief"),
        )

    def test_build_tool_registry_providers_from_settings_accepts_registry_file_shape(self) -> None:
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
                tool_registry_providers_json=json.dumps(
                    {
                        "file_provider": {
                            "registry_file": str(registry_file),
                            "extra_tools": {
                                "mock_plan_brief": {
                                    "template": "mock_plan",
                                    "label": "Brief Planner",
                                }
                            },
                        }
                    }
                )
            )

            providers = build_tool_registry_providers_from_settings(settings=settings)
            file_registry = providers["file_provider"].load_tool_registry()

        self.assertEqual(tuple(sorted(providers)), ("file_provider",))
        self.assertEqual(
            tuple(sorted(file_registry)),
            ("calc_eval_fast", "mock_plan_brief"),
        )

    def test_build_tool_registry_loaders_from_settings_accepts_registry_file_manifest_shape(self) -> None:
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
            settings = SimpleNamespace(
                tool_registry_loaders_json=json.dumps(
                    {
                        "file_loader": {
                            "registry_file": str(registry_file),
                            "extra_tools": {
                                "mock_plan_brief": {
                                    "template": "mock_plan",
                                    "label": "Brief Planner",
                                }
                            },
                        }
                    }
                )
            )

            loaders = build_tool_registry_loaders_from_settings(settings=settings)
            file_registry = loaders["file_loader"]()

        self.assertEqual(tuple(sorted(loaders)), ("file_loader",))
        self.assertEqual(
            tuple(sorted(file_registry)),
            ("calc_eval", "calc_eval_fast", "mock_plan_brief", "task_plan"),
        )
        self.assertEqual(file_registry["calc_eval"].label, "Planning Calculator")

    def test_build_tool_registry_loaders_from_settings_reuse_shared_profile_name_helper_for_registry_manifest(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "tool-registry-manifest.json"
            registry_file.write_text(
                json.dumps(
                    {
                        "profile": " Planning_Only ",
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
            settings = SimpleNamespace(
                tool_registry_loaders_json=json.dumps(
                    {
                        "file_loader": {
                            "registry_file": str(registry_file),
                            "extra_tools": {
                                "mock_plan_brief": {
                                    "template": "mock_plan",
                                    "label": "Brief Planner",
                                }
                            },
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
                    if (
                        getattr(settings, "tool_registry_profile", None)
                        == " Planning_Only "
                    ):
                        return "calculator_only"
                    return original_get_tool_registry_profile_name_from_settings(
                        settings=settings
                    )

                tool_runtime_module.get_tool_registry_profile_name_from_settings = (
                    fake_get_tool_registry_profile_name_from_settings
                )
                loaders = build_tool_registry_loaders_from_settings(settings=settings)
                file_registry = loaders["file_loader"]()
            finally:
                tool_runtime_module.get_tool_registry_profile_name_from_settings = (
                    original_get_tool_registry_profile_name_from_settings
                )

        self.assertEqual(tuple(sorted(loaders)), ("file_loader",))
        self.assertIn(" Planning_Only ", captured)
        self.assertEqual(
            tuple(sorted(file_registry)),
            ("calc_eval", "calc_eval_fast", "mock_plan_brief"),
        )

    def test_build_tool_registry_providers_from_settings_accepts_registry_file_manifest_shape(self) -> None:
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
            settings = SimpleNamespace(
                tool_registry_providers_json=json.dumps(
                    {
                        "file_provider": {
                            "registry_file": str(registry_file),
                            "disabled_tool_names": ["mock_retrieve"],
                            "extra_tools": {
                                "mock_plan_brief": {
                                    "template": "mock_plan",
                                    "label": "Brief Planner",
                                }
                            },
                        }
                    }
                )
            )

            providers = build_tool_registry_providers_from_settings(settings=settings)
            file_registry = providers["file_provider"].load_tool_registry()

        self.assertEqual(tuple(sorted(providers)), ("file_provider",))
        self.assertEqual(
            tuple(sorted(file_registry)),
            ("calc_eval", "calc_eval_fast", "mock_plan_brief"),
        )
        self.assertEqual(file_registry["calc_eval"].label, "Retrieval Calculator")

    def test_build_tool_registry_loaders_from_settings_accepts_named_loader_factory_backed_by_registry_file(self) -> None:
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
                ),
                tool_registry_loaders_json=json.dumps(
                    {
                        "file_loader": {
                            "loader_factory": "file_factory",
                            "extra_tools": {
                                "mock_plan_brief": {
                                    "template": "mock_plan",
                                    "label": "Brief Planner",
                                }
                            },
                        }
                    }
                ),
            )

            loaders = build_tool_registry_loaders_from_settings(settings=settings)
            file_registry = loaders["file_loader"]()

        self.assertEqual(tuple(sorted(loaders)), ("file_loader",))
        self.assertEqual(
            tuple(sorted(file_registry)),
            ("calc_eval_fast", "mock_plan_brief"),
        )

    def test_build_tool_registry_providers_from_settings_accepts_named_provider_factory_backed_by_registry_file(self) -> None:
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
                ),
                tool_registry_providers_json=json.dumps(
                    {
                        "file_provider": {
                            "provider_factory": "file_factory",
                            "extra_tools": {
                                "mock_plan_brief": {
                                    "template": "mock_plan",
                                    "label": "Brief Planner",
                                }
                            },
                        }
                    }
                ),
            )

            providers = build_tool_registry_providers_from_settings(settings=settings)
            file_registry = providers["file_provider"].load_tool_registry()

        self.assertEqual(tuple(sorted(providers)), ("file_provider",))
        self.assertEqual(
            tuple(sorted(file_registry)),
            ("calc_eval_fast", "mock_plan_brief"),
        )

    def test_build_tool_registry_providers_from_settings_accepts_named_loader_reference(self) -> None:
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
                    }
                }
            ),
            tool_registry_providers_json=json.dumps(
                {
                    "planning_provider": {
                        "loader": "planning_loader",
                        "disabled_tool_names": ["mock_plan"],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                }
            ),
        )

        providers = build_tool_registry_providers_from_settings(settings=settings)

        self.assertEqual(tuple(sorted(providers)), ("planning_provider",))
        self.assertEqual(
            get_registered_tool_names(registry_provider=providers["planning_provider"]),
            ("calc_eval", "calc_eval_fast"),
        )
        self.assertEqual(
            providers["planning_provider"].load_tool_registry()["calc_eval"].label,
            "Planning Calculator",
        )

    def test_build_tool_registry_providers_from_settings_accepts_named_loader_built_from_loader_factory(self) -> None:
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
                    }
                }
            ),
            tool_registry_providers_json=json.dumps(
                {
                    "planning_provider": {
                        "loader": "planning_loader",
                        "disabled_tool_names": ["mock_plan"],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                }
            ),
        )

        providers = build_tool_registry_providers_from_settings(settings=settings)

        self.assertEqual(tuple(sorted(providers)), ("planning_provider",))
        self.assertEqual(
            get_registered_tool_names(registry_provider=providers["planning_provider"]),
            ("calc_eval", "calc_eval_fast"),
        )
        self.assertEqual(
            providers["planning_provider"].load_tool_registry()["calc_eval"].label,
            "Planning Calculator",
        )

    def test_build_tool_registry_providers_from_settings_accepts_forward_named_provider_reference(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_providers_json=json.dumps(
                {
                    "outer_provider": {
                        "provider": "inner_provider",
                        "disabled_tool_names": ["mock_plan"],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    },
                    "inner_provider": {
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

        providers = build_tool_registry_providers_from_settings(settings=settings)

        self.assertEqual(tuple(sorted(providers)), ("inner_provider", "outer_provider"))
        self.assertEqual(
            get_registered_tool_names(registry_provider=providers["outer_provider"]),
            ("calc_eval", "calc_eval_fast"),
        )
        self.assertEqual(
            providers["outer_provider"].load_tool_registry()["calc_eval"].label,
            "Planning Calculator",
        )

    def test_build_tool_registry_providers_from_settings_accepts_loader_factory_reference(self) -> None:
        settings = SimpleNamespace(
            tool_registry_providers_json=json.dumps(
                {
                    "planning_provider": {
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

    def test_build_tool_registry_provider_sources_from_settings_accepts_named_provider_reference(self) -> None:
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
                        "disabled_tool_names": ["mock_plan"],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                }
            ),
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

    def test_build_tool_registry_provider_sources_from_settings_accepts_provider_factory_reference(self) -> None:
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
            ("calc_eval", "calc_eval_fast", "task_plan"),
        )
        self.assertEqual(
            sources["planning_suite"].load_tool_registry()["calc_eval"].label,
            "Planning Calculator",
        )

    def test_build_tool_registry_provider_sources_from_settings_accepts_loader_factory_reference(self) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_sources_json=json.dumps(
                {
                    "planning_suite": {
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

        sources = build_tool_registry_provider_sources_from_settings(settings=settings)

        self.assertEqual(tuple(sorted(sources)), ("planning_suite",))
        self.assertEqual(
            get_registered_tool_names(registry_provider=sources["planning_suite"]),
            ("calc_eval", "calc_eval_fast", "task_plan"),
        )
        self.assertEqual(
            sources["planning_suite"].load_tool_registry()["calc_eval"].label,
            "Planning Calculator",
        )

    def test_build_tool_registry_provider_sources_from_settings_accepts_named_loader_reference(self) -> None:
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
                    }
                }
            ),
            tool_registry_provider_sources_json=json.dumps(
                {
                    "planning_suite": {
                        "loader": "planning_loader",
                        "disabled_tool_names": ["mock_plan"],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                }
            ),
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

    def test_build_tool_registry_provider_sources_from_settings_accepts_named_loader_built_from_loader_factory(self) -> None:
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
                    }
                }
            ),
            tool_registry_provider_sources_json=json.dumps(
                {
                    "planning_suite": {
                        "loader": "planning_loader",
                        "disabled_tool_names": ["mock_plan"],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                }
            ),
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

    def test_build_tool_registry_provider_sources_from_settings_reuses_shared_profile_name_helper(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_sources_json=json.dumps(
                {
                    "planning_suite": {
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
            sources = build_tool_registry_provider_sources_from_settings(settings=settings)
        finally:
            tool_runtime_module.get_tool_registry_profile_name_from_settings = (
                original_get_tool_registry_profile_name_from_settings
            )

        self.assertEqual(tuple(sorted(sources)), ("planning_suite",))
        self.assertIn(" Planning_Only ", captured)
        self.assertEqual(
            get_registered_tool_names(registry_provider=sources["planning_suite"]),
            ("calc_eval",),
        )

    def test_build_tool_registry_provider_sources_from_settings_reuses_shared_provider_source_name_helper(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_sources_json=json.dumps(
                {
                    " Planning_Suite ": {
                        "calc_eval_fast": {
                            "template": "calc_eval",
                            "label": "Fast Calculator",
                        }
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
                captured.append(getattr(settings, "tool_registry_provider_source", None))
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
            sources = build_tool_registry_provider_sources_from_settings(settings=settings)
        finally:
            tool_runtime_module.get_tool_registry_provider_source_name_from_settings = (
                original_get_tool_registry_provider_source_name_from_settings
            )

        self.assertIn(" Planning_Suite ", captured)
        self.assertEqual(tuple(sorted(sources)), ("planning_suite_shadow",))
        self.assertEqual(
            get_registered_tool_names(registry_provider=sources["planning_suite_shadow"]),
            ("calc_eval_fast",),
        )

    def test_build_tool_registry_provider_sources_from_settings_reuses_shared_provider_source_name_helper_for_forward_source_reference(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_sources_json=json.dumps(
                {
                    " Outer_Suite ": {
                        "provider": " Inner_Suite ",
                        "overrides": {
                            "calc_eval_fast": {
                                "label": "Outer Calculator",
                            }
                        },
                    },
                    " Inner_Suite ": {
                        "calc_eval_fast": {
                            "template": "calc_eval",
                            "label": "Inner Calculator",
                        }
                    },
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
                raw_source = getattr(settings, "tool_registry_provider_source", None)
                captured.append(raw_source)
                if raw_source == " Outer_Suite ":
                    return "outer_suite_shadow"
                if raw_source == " Inner_Suite ":
                    return "inner_suite_shadow"
                return original_get_tool_registry_provider_source_name_from_settings(
                    settings=settings
                )

            tool_runtime_module.get_tool_registry_provider_source_name_from_settings = (
                fake_get_tool_registry_provider_source_name_from_settings
            )
            sources = build_tool_registry_provider_sources_from_settings(settings=settings)
        finally:
            tool_runtime_module.get_tool_registry_provider_source_name_from_settings = (
                original_get_tool_registry_provider_source_name_from_settings
            )

        self.assertIn(" Outer_Suite ", captured)
        self.assertIn(" Inner_Suite ", captured)
        self.assertEqual(
            tuple(sorted(sources)),
            ("inner_suite_shadow", "outer_suite_shadow"),
        )
        self.assertEqual(
            get_registered_tool_names(registry_provider=sources["outer_suite_shadow"]),
            ("calc_eval_fast",),
        )
        self.assertEqual(
            sources["outer_suite_shadow"].load_tool_registry()[
                "calc_eval_fast"
            ].label,
            "Outer Calculator",
        )

    def test_build_tool_registry_provider_sources_from_settings_reports_source_provider_cycle_as_skipped(
        self,
    ) -> None:
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

        artifacts = build_tool_registry_provider_sources_from_settings_artifacts(
            settings=settings
        )

        self.assertEqual(artifacts["sources"], {})
        self.assertEqual(
            artifacts["source_diagnostics"]["outer_suite"]["skipped_registry_sources"],
            ("inner_suite",),
        )
        self.assertEqual(
            artifacts["source_diagnostics"]["inner_suite"]["skipped_registry_sources"],
            ("outer_suite",),
        )
        self.assertEqual(
            artifacts["source_diagnostics"]["outer_suite"]["missing_registry_sources"],
            (),
        )
        self.assertEqual(
            artifacts["source_diagnostics"]["inner_suite"]["missing_registry_sources"],
            (),
        )

    def test_get_configured_tool_registry_provider_artifacts_reuses_shared_provider_source_name_helper_for_forward_source_diagnostics(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            inner_file = Path(tmpdir) / "inner-source-registry.json"
            missing_file = Path(tmpdir) / "missing-child.json"
            inner_file.write_text(
                json.dumps(
                    {
                        "registry_files": [str(missing_file)],
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Inner Calculator",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            settings = SimpleNamespace(
                tool_registry_provider_source=" Outer_Suite ",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        " Outer_Suite ": {
                            "provider": " Inner_Suite ",
                            "overrides": {
                                "calc_eval_fast": {
                                    "label": "Outer Calculator",
                                }
                            },
                        },
                        " Inner_Suite ": {
                            "registry_file": str(inner_file),
                        },
                    }
                ),
            )
            original_get_tool_registry_provider_source_name_from_settings = (
                tool_runtime_module.get_tool_registry_provider_source_name_from_settings
            )
            try:
                def fake_get_tool_registry_provider_source_name_from_settings(
                    *,
                    settings=None,
                ):
                    raw_source = getattr(settings, "tool_registry_provider_source", None)
                    if raw_source == " Outer_Suite ":
                        return "outer_suite_shadow"
                    if raw_source == " Inner_Suite ":
                        return "inner_suite_shadow"
                    return original_get_tool_registry_provider_source_name_from_settings(
                        settings=settings
                    )

                tool_runtime_module.get_tool_registry_provider_source_name_from_settings = (
                    fake_get_tool_registry_provider_source_name_from_settings
                )
                artifacts = get_configured_tool_registry_provider_artifacts(
                    settings=settings
                )
            finally:
                tool_runtime_module.get_tool_registry_provider_source_name_from_settings = (
                    original_get_tool_registry_provider_source_name_from_settings
                )

        self.assertEqual(artifacts["provider_source_name"], "outer_suite_shadow")
        self.assertEqual(
            tuple(sorted(artifacts["provider"].load_tool_registry())),
            ("calc_eval_fast",),
        )
        self.assertEqual(
            artifacts["provider"].load_tool_registry()["calc_eval_fast"].label,
            "Outer Calculator",
        )
        self.assertEqual(
            artifacts["selected_source_diagnostics"]["missing_registry_files"],
            (str(missing_file.resolve()),),
        )

    def test_build_tool_registry_providers_from_settings_ignores_unknown_loader_name(self) -> None:
        settings = SimpleNamespace(
            tool_registry_providers_json=json.dumps(
                {
                    "broken_provider": {
                        "loader": "missing_loader",
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                            }
                        },
                    }
                }
            )
        )

        providers = build_tool_registry_providers_from_settings(settings=settings)

        self.assertEqual(providers, {})

    def test_build_tool_registry_loaders_from_settings_ignores_unknown_loader_name(self) -> None:
        settings = SimpleNamespace(
            tool_registry_loaders_json=json.dumps(
                {
                    "broken_loader": {
                        "loader": "missing_loader",
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                            }
                        },
                    }
                }
            )
        )

        loaders = build_tool_registry_loaders_from_settings(settings=settings)

        self.assertEqual(loaders, {})

    def test_build_tool_registry_loaders_from_settings_ignores_unknown_loader_factory_name(self) -> None:
        settings = SimpleNamespace(
            tool_registry_loaders_json=json.dumps(
                {
                    "broken_loader": {
                        "loader_factory": "missing_factory",
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                            }
                        },
                    }
                }
            )
        )

        loaders = build_tool_registry_loaders_from_settings(settings=settings)

        self.assertEqual(loaders, {})

    def test_build_tool_registry_loader_factories_from_settings_ignores_unknown_factory_name(self) -> None:
        settings = SimpleNamespace(
            tool_registry_loader_factories_json=json.dumps(
                {
                    "broken_factory": {
                        "factory": "missing_factory",
                    }
                }
            )
        )

        factories = build_tool_registry_loader_factories_from_settings(settings=settings)

        self.assertEqual(factories, {})

    def test_build_tool_registry_provider_factories_from_settings_ignores_unknown_factory_name(self) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_factories_json=json.dumps(
                {
                    "broken_factory": {
                        "factory": "missing_factory",
                    }
                }
            )
        )

        factories = build_tool_registry_provider_factories_from_settings(settings=settings)

        self.assertEqual(factories, {})

    def test_build_tool_registry_providers_from_settings_ignores_unknown_provider_factory_name(self) -> None:
        settings = SimpleNamespace(
            tool_registry_providers_json=json.dumps(
                {
                    "broken_provider": {
                        "provider_factory": "missing_factory",
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                            }
                        },
                    }
                }
            )
        )

        providers = build_tool_registry_providers_from_settings(settings=settings)

        self.assertEqual(providers, {})

    def test_build_tool_registry_overrides_from_settings_ignores_unknown_tools_and_bad_shapes(self) -> None:
        settings = SimpleNamespace(
            tool_registry_overrides_json=json.dumps(
                {
                    "unknown_tool": {"label": "Ignored"},
                    "calc_eval": "bad-shape",
                }
            )
        )

        overrides = build_tool_registry_overrides_from_settings(settings=settings)

        self.assertEqual(overrides, {})

    def test_build_tool_registry_settings_config_ignores_unknown_disabled_tools(self) -> None:
        settings = SimpleNamespace(
            tool_registry_overrides_json=json.dumps(
                {
                    "unknown_tool": {"enabled": False},
                    "calc_eval": "bad-shape",
                }
            )
        )

        config = build_tool_registry_settings_config(settings=settings)

        self.assertEqual(config.overrides, {})
        self.assertEqual(config.disabled_tool_names, ())

    def test_get_configured_tool_registry_provider_applies_settings_overrides(self) -> None:
        settings = SimpleNamespace(
            tool_registry_overrides_json=json.dumps(
                {
                    "calc_eval": {
                        "label": "Configured Calculator",
                        "default_timeout_ms": 8_888,
                        "requires_user_context": False,
                    }
                }
            )
        )

        provider = get_configured_tool_registry_provider(settings=settings)

        self.assertIsInstance(provider, ConfiguredToolRegistryProvider)
        runtime_ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
            registry_provider=provider,
        )
        self.assertEqual(runtime_ctx.registration.label, "Configured Calculator")
        self.assertEqual(runtime_ctx.default_timeout_ms, 8_888)
        self.assertEqual(runtime_ctx.user_id, "")

    def test_get_configured_tool_registry_provider_uses_selected_provider_source(self) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_source="analytics_suite",
            tool_registry_provider_sources_json=json.dumps(
                {
                    "analytics_suite": {
                        "calc_eval_fast": {
                            "template": "calc_eval",
                            "label": "Fast Calculator",
                            "default_timeout_ms": 1_500,
                        }
                    }
                }
            ),
            tool_registry_profile="default",
            tool_registry_overrides_json=None,
            tool_registry_extra_tools_json=None,
        )

        provider = get_configured_tool_registry_provider(settings=settings)

        self.assertEqual(
            get_registered_tool_names(registry_provider=provider),
            ("calc_eval_fast",),
        )
        runtime_ctx = build_tool_runtime_context(
            name="calc_eval_fast",
            prompt="calc",
            user_id="user-1",
            attempt=0,
            registry_provider=provider,
        )
        self.assertEqual(runtime_ctx.registration.label, "Fast Calculator")
        self.assertEqual(runtime_ctx.default_timeout_ms, 1_500)

    def test_get_configured_tool_registry_provider_stacks_global_settings_on_selected_source(self) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_source="planning_suite",
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
                    }
                }
            ),
            tool_registry_profile="default",
            tool_registry_overrides_json=json.dumps(
                {
                    "calc_eval": {
                        "default_timeout_ms": 1_200,
                    }
                }
            ),
            tool_registry_extra_tools_json=json.dumps(
                {
                    "calc_eval_fast": {
                        "template": "calc_eval",
                        "label": "Global Fast Calculator",
                    }
                }
            ),
        )

        provider = get_configured_tool_registry_provider(settings=settings)

        self.assertEqual(
            get_registered_tool_names(registry_provider=provider),
            ("calc_eval", "calc_eval_fast"),
        )
        runtime_ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
            registry_provider=provider,
        )
        self.assertEqual(runtime_ctx.registration.label, "Planning Calculator")
        self.assertEqual(runtime_ctx.default_timeout_ms, 1_200)

    def test_get_configured_tool_registry_provider_uses_selected_source_backed_by_named_provider(self) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_source="planning_suite",
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
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                }
            ),
            tool_registry_profile="default",
            tool_registry_overrides_json=json.dumps(
                {
                    "calc_eval": {
                        "default_timeout_ms": 1_200,
                    }
                }
            ),
            tool_registry_extra_tools_json=None,
        )

        provider = get_configured_tool_registry_provider(settings=settings)
        runtime_ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
            registry_provider=provider,
        )

        self.assertEqual(runtime_ctx.registration.label, "Planning Calculator")
        self.assertEqual(runtime_ctx.default_timeout_ms, 1_200)
        self.assertEqual(
            get_registered_tool_names(registry_provider=provider),
            ("calc_eval", "calc_eval_fast", "task_plan"),
        )

    def test_get_configured_tool_registry_provider_uses_selected_source_backed_by_provider_factory(self) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_source="planning_suite",
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
                        "extra_tools": {
                            "calc_eval_fast": {
                                "template": "calc_eval",
                                "label": "Fast Calculator",
                            }
                        },
                    }
                }
            ),
            tool_registry_profile="default",
            tool_registry_overrides_json=json.dumps(
                {
                    "calc_eval": {
                        "default_timeout_ms": 1_200,
                    }
                }
            ),
            tool_registry_extra_tools_json=None,
        )

        provider = get_configured_tool_registry_provider(settings=settings)
        runtime_ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
            registry_provider=provider,
        )

        self.assertEqual(runtime_ctx.registration.label, "Planning Calculator")
        self.assertEqual(runtime_ctx.default_timeout_ms, 1_200)
        self.assertEqual(
            get_registered_tool_names(registry_provider=provider),
            ("calc_eval", "calc_eval_fast", "task_plan"),
        )

    def test_get_configured_tool_registry_provider_uses_provider_factory_alias_profile_override(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_source="planning_suite",
            tool_registry_provider_factories_json=json.dumps(
                {
                    "outer_factory": {
                        "factory": "retrieval_only",
                        "profile": "default",
                    }
                }
            ),
            tool_registry_provider_sources_json=json.dumps(
                {
                    "planning_suite": {
                        "provider_factory": "outer_factory",
                    }
                }
            ),
            tool_registry_profile="default",
            tool_registry_overrides_json=None,
            tool_registry_extra_tools_json=None,
        )

        provider = get_configured_tool_registry_provider(settings=settings)

        self.assertEqual(
            get_registered_tool_names(registry_provider=provider),
            ("calc_eval", "task_plan", "task_retrieve"),
        )

    def test_get_configured_tool_registry_provider_uses_provider_factory_profile_override(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_source="planning_suite",
            tool_registry_provider_sources_json=json.dumps(
                {
                    "planning_suite": {
                        "provider_factory": "retrieval_only",
                        "profile": "default",
                    }
                }
            ),
            tool_registry_profile="default",
            tool_registry_overrides_json=None,
            tool_registry_extra_tools_json=None,
        )

        provider = get_configured_tool_registry_provider(settings=settings)

        self.assertEqual(
            get_registered_tool_names(registry_provider=provider),
            ("calc_eval", "task_plan", "task_retrieve"),
        )

    def test_get_configured_tool_registry_provider_uses_selected_source_backed_by_loader_factory(self) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_source="planning_suite",
            tool_registry_provider_sources_json=json.dumps(
                {
                    "planning_suite": {
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
            ),
            tool_registry_profile="default",
            tool_registry_overrides_json=json.dumps(
                {
                    "calc_eval": {
                        "default_timeout_ms": 1_200,
                    }
                }
            ),
            tool_registry_extra_tools_json=None,
        )

        provider = get_configured_tool_registry_provider(settings=settings)
        runtime_ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
            registry_provider=provider,
        )

        self.assertEqual(runtime_ctx.registration.label, "Planning Calculator")
        self.assertEqual(runtime_ctx.default_timeout_ms, 1_200)
        self.assertEqual(
            get_registered_tool_names(registry_provider=provider),
            ("calc_eval", "calc_eval_fast", "task_plan"),
        )

    def test_get_configured_tool_registry_provider_uses_loader_factory_profile_override(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_source="planning_suite",
            tool_registry_provider_sources_json=json.dumps(
                {
                    "planning_suite": {
                        "loader_factory": "retrieval_only",
                        "profile": "default",
                    }
                }
            ),
            tool_registry_profile="default",
            tool_registry_overrides_json=None,
            tool_registry_extra_tools_json=None,
        )

        provider = get_configured_tool_registry_provider(settings=settings)

        self.assertEqual(
            get_registered_tool_names(registry_provider=provider),
            ("calc_eval", "task_plan", "task_retrieve"),
        )

    def test_get_configured_tool_registry_provider_includes_extra_tools(self) -> None:
        settings = SimpleNamespace(
            tool_registry_profile="default",
            tool_registry_overrides_json=json.dumps(
                {
                    "calc_eval_fast": {
                        "requires_user_context": False,
                    }
                }
            ),
            tool_registry_extra_tools_json=json.dumps(
                {
                    "calc_eval_fast": {
                        "template": "calc_eval",
                        "label": "Fast Calculator",
                        "default_timeout_ms": 1_500,
                    }
                }
            ),
        )

        provider = get_configured_tool_registry_provider(settings=settings)

        self.assertEqual(
            get_registered_tool_names(registry_provider=provider),
            ("calc_eval", "calc_eval_fast", "task_plan", "task_retrieve"),
        )
        runtime_ctx = build_tool_runtime_context(
            name="calc_eval_fast",
            prompt="calc",
            user_id="user-1",
            attempt=0,
            registry_provider=provider,
        )
        self.assertEqual(runtime_ctx.registration.label, "Fast Calculator")
        self.assertEqual(runtime_ctx.default_timeout_ms, 1_500)
        self.assertEqual(runtime_ctx.user_id, "")

    def test_get_configured_tool_registry_provider_applies_profile_disabled_tools(self) -> None:
        settings = SimpleNamespace(
            tool_registry_profile="planning_only",
            tool_registry_overrides_json=None,
        )

        provider = get_configured_tool_registry_provider(settings=settings)

        self.assertEqual(
            get_registered_tool_names(registry_provider=provider),
            ("task_plan",),
        )

    def test_get_configured_tool_registry_provider_filters_disabled_tools(self) -> None:
        settings = SimpleNamespace(
            tool_registry_overrides_json=json.dumps(
                {
                    "mock_retrieve": {"enabled": False},
                }
            )
        )

        provider = get_configured_tool_registry_provider(settings=settings)

        self.assertIsInstance(provider, ConfiguredToolRegistryProvider)
        self.assertEqual(
            get_registered_tool_names(registry_provider=provider),
            ("calc_eval", "task_plan"),
        )
        with self.assertRaises(MockToolExecutionError) as ctx:
            ensure_tool_registration(
                "mock_retrieve",
                registry_provider=provider,
            )
        self.assertEqual(str(ctx.exception), "Unknown tool: mock_retrieve")

    def test_get_tool_registry_profile_name_from_settings_defaults_to_default(self) -> None:
        settings = SimpleNamespace(tool_registry_profile=None)

        self.assertEqual(
            get_tool_registry_profile_name_from_settings(settings=settings),
            "default",
        )

    def test_get_tool_registry_provider_source_name_from_settings_defaults_to_default(self) -> None:
        settings = SimpleNamespace(tool_registry_provider_source=None)

        self.assertEqual(
            get_tool_registry_provider_source_name_from_settings(settings=settings),
            "default",
        )

    def test_get_tool_registry_provider_source_specs_from_settings_normalizes_named_specs(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_provider_sources_json=json.dumps(
                {
                    " Suite_A ": {
                        "provider": "default",
                        "profile": "planning_only",
                    },
                    "default": {
                        "provider": "default",
                        "profile": "default",
                    },
                    "broken": [],
                }
            )
        )

        self.assertEqual(
            tool_runtime_module.get_tool_registry_provider_source_specs_from_settings(
                settings=settings
            ),
            {
                "suite_a": {
                    "provider": "default",
                    "profile": "planning_only",
                }
            },
        )

    def test_tool_registry_profile_and_source_helpers_reuse_shared_reference_normalizer(
        self,
    ) -> None:
        settings = SimpleNamespace(
            tool_registry_profile=" Planning_Only ",
            tool_registry_provider_source=" Planning_Suite ",
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
                if name == " Planning_Only ":
                    return "calculator_only"
                if name == " Planning_Suite ":
                    return "planning_suite_shadow"
                if not isinstance(name, str):
                    return None
                normalized = name.strip().lower()
                return normalized or None

            tool_runtime_module._normalize_named_tool_registry_component_name = (
                fake_normalize_named_tool_registry_component_name
            )
            profile_name = get_tool_registry_profile_name_from_settings(settings=settings)
            provider_source_name = get_tool_registry_provider_source_name_from_settings(
                settings=settings
            )
        finally:
            tool_runtime_module._normalize_named_tool_registry_component_name = (
                original_normalize_named_tool_registry_component_name
            )

        self.assertIn(" Planning_Only ", captured)
        self.assertIn(" Planning_Suite ", captured)
        self.assertEqual(profile_name, "calculator_only")
        self.assertEqual(provider_source_name, "planning_suite_shadow")

    def test_load_tool_registry_returns_isolated_default_snapshot(self) -> None:
        registry = load_tool_registry()

        self.assertEqual(
            tuple(sorted(registry)),
            ("calc_eval", "task_plan", "task_retrieve"),
        )
        registry.pop("task_plan")
        self.assertEqual(
            get_registered_tool_names(),
            ("calc_eval", "task_plan", "task_retrieve"),
        )

    def test_load_tool_registry_applies_overrides_on_fresh_snapshot(self) -> None:
        registry = load_tool_registry(
            overrides={
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="custom_calc",
                    label="Custom Calculator",
                    retryable_by_default=False,
                    default_timeout_ms=9_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "tool_input": tool_input,
                        "prompt": prompt,
                        "user_id": user_id,
                    },
                ),
                "custom_lookup": ToolRegistration(
                    name="custom_lookup",
                    kind="custom_lookup",
                    label="Custom Lookup",
                    retryable_by_default=False,
                    default_timeout_ms=12_000,
                    requires_user_context=False,
                    supports_result_preview=False,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "tool_input": tool_input,
                        "prompt": prompt,
                        "user_id": user_id,
                    },
                ),
            }
        )

        self.assertEqual(
            get_registered_tool_names(registry=registry),
            ("calc_eval", "custom_lookup", "task_plan", "task_retrieve"),
        )
        self.assertEqual(
            resolve_tool_registration("calc_eval", registry=registry).kind,
            "custom_calc",
        )
        self.assertIsNotNone(resolve_tool_registration("custom_lookup", registry=registry))
        self.assertEqual(
            get_registered_tool_names(),
            ("calc_eval", "task_plan", "task_retrieve"),
        )

    def test_load_tool_registry_accepts_custom_loader_then_applies_overrides(self) -> None:
        def custom_loader() -> dict[str, ToolRegistration]:
            return {
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="loader_calc",
                    label="Loader Calculator",
                    retryable_by_default=False,
                    default_timeout_ms=11_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "tool_input": tool_input,
                        "prompt": prompt,
                        "user_id": user_id,
                    },
                )
            }

        registry = load_tool_registry(
            loader=custom_loader,
            overrides={
                "custom_lookup": ToolRegistration(
                    name="custom_lookup",
                    kind="custom_lookup",
                    label="Custom Lookup",
                    retryable_by_default=False,
                    default_timeout_ms=12_000,
                    requires_user_context=False,
                    supports_result_preview=False,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "tool_input": tool_input,
                        "prompt": prompt,
                        "user_id": user_id,
                    },
                )
            },
        )

        self.assertEqual(
            get_registered_tool_names(registry=registry),
            ("calc_eval", "custom_lookup"),
        )
        self.assertEqual(
            resolve_tool_registration("calc_eval", registry=registry).kind,
            "loader_calc",
        )

    def test_load_tool_registry_accepts_provider_then_applies_overrides(self) -> None:
        provider = StaticToolRegistryProvider(
            registry={
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="provider_calc",
                    label="Provider Calculator",
                    retryable_by_default=False,
                    default_timeout_ms=13_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "tool_input": tool_input,
                        "prompt": prompt,
                        "user_id": user_id,
                    },
                )
            }
        )

        registry = load_tool_registry(
            provider=provider,
            overrides={
                "custom_lookup": ToolRegistration(
                    name="custom_lookup",
                    kind="custom_lookup",
                    label="Custom Lookup",
                    retryable_by_default=False,
                    default_timeout_ms=12_000,
                    requires_user_context=False,
                    supports_result_preview=False,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "tool_input": tool_input,
                        "prompt": prompt,
                        "user_id": user_id,
                    },
                )
            },
        )

        self.assertEqual(
            get_registered_tool_names(registry=registry),
            ("calc_eval", "custom_lookup"),
        )
        self.assertEqual(
            resolve_tool_registration("calc_eval", registry=registry).kind,
            "provider_calc",
        )

    def test_load_tool_registry_uses_default_provider_when_no_source_is_given(self) -> None:
        original = tool_runtime_module.get_default_tool_registry_provider

        def fake_default_provider() -> StaticToolRegistryProvider:
            return StaticToolRegistryProvider(
                registry={
                    "custom_only": ToolRegistration(
                        name="custom_only",
                        kind="custom_only",
                        label="Custom Only",
                        retryable_by_default=False,
                        default_timeout_ms=7_000,
                        requires_user_context=False,
                        supports_result_preview=False,
                        runner=lambda *, tool_input, prompt, user_id: {
                            "tool_input": tool_input,
                            "prompt": prompt,
                            "user_id": user_id,
                        },
                    )
                }
            )

        tool_runtime_module.get_default_tool_registry_provider = fake_default_provider
        try:
            registry = load_tool_registry()
        finally:
            tool_runtime_module.get_default_tool_registry_provider = original

        self.assertEqual(tuple(sorted(registry)), ("custom_only",))

    def test_execute_tool_plan_item_service_execution_accepts_built_registry_provider(self) -> None:
        runner_calls: list[tuple[dict[str, object], str, str]] = []

        def custom_runner(
            *,
            tool_input: dict[str, object],
            prompt: str,
            user_id: str,
        ) -> dict[str, object]:
            runner_calls.append((tool_input, prompt, user_id))
            return {
                "result": "provider-ok",
                "tool_kind": "provider_calc",
            }

        provider = build_tool_registry_provider(
            provider=StaticToolRegistryProvider(
                registry={
                    "calc_eval": ToolRegistration(
                        name="calc_eval",
                        kind="provider_calc",
                        label="Provider Calculator",
                        retryable_by_default=False,
                        default_timeout_ms=13_000,
                        requires_user_context=False,
                        supports_result_preview=True,
                        runner=custom_runner,
                    )
                }
            )
        )
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )

        items = list(
            execute_tool_plan_item_service_execution(
                task_id="task-1",
                trace_steps=[{"id": "existing-1", "seq": 2, "content": "Existing"}],
                iteration_ctx=iteration_ctx,
                initial_action_step=iteration_ctx["action_step"],
                tool_name="calc_eval",
                tool_input={"expression": "1+2*3"},
                prompt="calc",
                user_id="user-1",
                model="mock-gpt",
                estimate_token_count=lambda text: len(text.strip()) or 0,
                make_step_id=lambda: "rag-unused",
                raise_if_should_abort=lambda: None,
                registry_provider=provider,
            )
        )

        self.assertEqual(runner_calls, [({"expression": "1+2*3"}, "calc", "")])
        final_item = items[-1]
        self.assertEqual(final_item["kind"], "result")
        self.assertEqual(
            final_item["result"]["loop_execution_result"]["success_effects"]["output"],
            {
                "result": "provider-ok",
            },
        )

    def test_build_tool_registry_merges_overrides_without_mutating_default(self) -> None:
        custom_registry = build_tool_registry(
            overrides={
                "calc_eval": ToolRegistration(
                    name="calc_eval",
                    kind="custom_calc",
                    label="Custom Calculator",
                    retryable_by_default=False,
                    default_timeout_ms=9_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "tool_input": tool_input,
                        "prompt": prompt,
                        "user_id": user_id,
                    },
                ),
                "custom_lookup": ToolRegistration(
                    name="custom_lookup",
                    kind="custom_lookup",
                    label="Custom Lookup",
                    retryable_by_default=False,
                    default_timeout_ms=12_000,
                    requires_user_context=False,
                    supports_result_preview=False,
                    runner=lambda *, tool_input, prompt, user_id: {
                        "tool_input": tool_input,
                        "prompt": prompt,
                        "user_id": user_id,
                    },
                ),
            }
        )

        self.assertEqual(
            get_registered_tool_names(registry=custom_registry),
            ("calc_eval", "custom_lookup", "task_plan", "task_retrieve"),
        )
        self.assertEqual(
            resolve_tool_registration("calc_eval", registry=custom_registry).kind,
            "custom_calc",
        )
        self.assertIsNotNone(resolve_tool_registration("custom_lookup", registry=custom_registry))
        self.assertEqual(
            get_registered_tool_names(),
            ("calc_eval", "task_plan", "task_retrieve"),
        )

    def test_normalize_tool_spec_coerces_name_and_defaults_input(self) -> None:
        invocation = normalize_tool_spec(
            {
                "name": 123,
                "input": "not-a-dict",
            }
        )

        self.assertEqual(invocation.name, "123")
        self.assertEqual(invocation.tool_input, {})

    def test_normalize_tool_spec_accepts_mapping_wrappers(self) -> None:
        invocation = normalize_tool_spec(
            UserDict(
                {
                    UserString("name"): UserString("calc_eval"),
                    UserString("input"): UserDict(
                        {UserString("expression"): UserString("1+2")}
                    ),
                }
            )
        )

        self.assertEqual(invocation.name, "calc_eval")
        self.assertEqual(invocation.tool_input, {"expression": "1+2"})

    def test_resolve_tool_registration_exposes_explicit_calc_entry(self) -> None:
        registration = resolve_tool_registration("calc_eval")

        self.assertIsNotNone(registration)
        assert registration is not None
        self.assertEqual(registration.name, "calc_eval")
        self.assertEqual(registration.kind, "local_calculator")
        self.assertEqual(registration.label, "Calculator")
        self.assertTrue(registration.retryable_by_default)
        self.assertEqual(registration.default_timeout_ms, 3_000)
        self.assertTrue(registration.requires_user_context)
        self.assertTrue(registration.supports_result_preview)

    def test_build_tool_result_preview_governs_builtin_calc_preview_fields(self) -> None:
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        self.assertEqual(
            build_tool_result_preview(name="calc_eval", output=output),
            {
                "expression": "1+2*3",
                "result": 7.0,
            },
        )

    def test_build_tool_result_preview_governs_builtin_retrieval_preview_fields(
        self,
    ) -> None:
        output = {
            "chunks": ["alpha", "beta"],
            "hits": [{"content": "alpha"}],
            "hit_count": 2,
            "knowledge_base_id": "demo-kb",
            "collection": "user-demo-kb",
        }

        self.assertEqual(
            build_tool_result_preview(name="task_retrieve", output=output),
            {
                "hit_count": 2,
                "knowledge_base_id": "demo-kb",
            },
        )

    def test_build_tool_result_preview_uses_explicit_result_preview_keys(self) -> None:
        output = {
            "tool_kind": "knowledge_retrieval",
            "chunks": ["alpha", "beta"],
            "hit_count": 2,
            "knowledge_base_id": "demo-kb",
            "raw_documents": [{"id": "doc-1"}],
        }
        registration = ToolRegistration(
            name="task_retrieve_hot",
            kind="knowledge_retrieval",
            label="Hot Retrieval",
            retryable_by_default=True,
            default_timeout_ms=5_000,
            requires_user_context=True,
            supports_result_preview=True,
            runner=lambda *, tool_input, prompt, user_id: {
                "tool_input": tool_input,
            },
            result_preview_keys=("tool_kind", "hit_count", "knowledge_base_id"),
        )

        self.assertEqual(
            build_tool_result_preview(
                name="task_retrieve_hot",
                output=output,
                registration=registration,
            ),
            {
                "tool_kind": "knowledge_retrieval",
                "hit_count": 2,
                "knowledge_base_id": "demo-kb",
            },
        )

    def test_get_tool_semantic_kind_normalizes_extra_provider_planner_kind(self) -> None:
        registration = ToolRegistration(
            name="provider_plan",
            kind="provider_planner",
            label="Provider Planner",
            retryable_by_default=False,
            default_timeout_ms=8_000,
            requires_user_context=False,
            supports_result_preview=True,
            runner=lambda *, tool_input, prompt, user_id: {
                "tool_input": tool_input,
            },
        )

        self.assertEqual(
            get_tool_semantic_kind(
                name="provider_plan",
                registration=registration,
            ),
            "task_planner",
        )

    def test_build_tool_result_preview_infers_preview_shape_for_extra_provider_planner_kind(
        self,
    ) -> None:
        output = {
            "plan": "Analyze request -> Synthesize final answer",
            "steps": [
                "Analyze request",
                "Synthesize final answer",
            ],
            "tool_kind": "provider_planner",
            "raw_payload": {"audit": "keep-raw-only"},
        }
        registration = ToolRegistration(
            name="provider_plan",
            kind="provider_planner",
            label="Provider Planner",
            retryable_by_default=False,
            default_timeout_ms=8_000,
            requires_user_context=False,
            supports_result_preview=True,
            runner=lambda *, tool_input, prompt, user_id: {
                "tool_input": tool_input,
            },
        )

        self.assertEqual(
            build_tool_result_preview(
                name="provider_plan",
                output=output,
                registration=registration,
            ),
            {
                "plan": "Analyze request -> Synthesize final answer",
                "steps": [
                    "Analyze request",
                    "Synthesize final answer",
                ],
            },
        )

    def test_build_tool_result_preview_infers_preview_shape_for_extra_provider_planner_kind_with_tuple_steps(
        self,
    ) -> None:
        output = {
            "plan": "Analyze request -> Synthesize final answer",
            "steps": (
                "Analyze request",
                "Synthesize final answer",
            ),
            "tool_kind": "provider_planner",
            "raw_payload": {"audit": "keep-raw-only"},
        }
        registration = ToolRegistration(
            name="provider_plan",
            kind="provider_planner",
            label="Provider Planner",
            retryable_by_default=False,
            default_timeout_ms=8_000,
            requires_user_context=False,
            supports_result_preview=True,
            runner=lambda *, tool_input, prompt, user_id: {
                "tool_input": tool_input,
            },
        )

        self.assertEqual(
            build_tool_result_preview(
                name="provider_plan",
                output=output,
                registration=registration,
            ),
            {
                "plan": "Analyze request -> Synthesize final answer",
                "steps": [
                    "Analyze request",
                    "Synthesize final answer",
                ],
            },
        )

    def test_tool_runtime_helpers_expose_current_calc_defaults(self) -> None:
        self.assertTrue(tool_requires_user_context("calc_eval"))
        self.assertTrue(is_tool_retryable_by_default("calc_eval"))
        self.assertEqual(get_tool_default_timeout_ms("calc_eval"), 3_000)

    def test_ensure_tool_registration_keeps_unknown_tool_fatal(self) -> None:
        with self.assertRaises(MockToolExecutionError) as ctx:
            ensure_tool_registration("does_not_exist")

        self.assertTrue(ctx.exception.fatal)
        self.assertIn("unknown tool", str(ctx.exception).lower())

    def test_maybe_raise_tool_execution_error_keeps_transient_semantics(self) -> None:
        with self.assertRaises(MockToolExecutionError) as ctx:
            maybe_raise_tool_execution_error(
                name="mock_plan",
                prompt="[tool-error]",
                attempt=0,
            )

        self.assertFalse(ctx.exception.fatal)
        self.assertIn("transient error", str(ctx.exception).lower())

    def test_maybe_raise_mock_tool_execution_error_keeps_legacy_marker_compatibility(self) -> None:
        with self.assertRaises(MockToolExecutionError) as ctx:
            maybe_raise_mock_tool_execution_error(
                name="mock_plan",
                prompt="[mock-tool-error]",
                attempt=0,
            )

        self.assertFalse(ctx.exception.fatal)
        self.assertIn("transient error", str(ctx.exception).lower())

    def test_build_tool_runtime_context_keeps_calc_defaults(self) -> None:
        ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )

        self.assertEqual(ctx.name, "calc_eval")
        self.assertEqual(ctx.user_id, "user-1")
        self.assertEqual(ctx.attempt, 0)
        self.assertEqual(ctx.default_timeout_ms, 3_000)
        self.assertTrue(ctx.retryable_by_default)
        self.assertTrue(ctx.requires_user_context)

    def test_build_tool_runtime_context_accepts_custom_registry_metadata(self) -> None:
        registry = {
            "calc_eval": ToolRegistration(
                name="calc_eval",
                kind="custom_calc",
                label="Custom Calculator",
                retryable_by_default=False,
                default_timeout_ms=9_000,
                requires_user_context=False,
                supports_result_preview=False,
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_input": tool_input,
                    "prompt": prompt,
                    "user_id": user_id,
                },
            )
        }

        ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="custom-calc",
            user_id="user-1",
            attempt=2,
            registry=registry,
        )

        self.assertEqual(ctx.name, "calc_eval")
        self.assertEqual(ctx.user_id, "")
        self.assertEqual(ctx.attempt, 2)
        self.assertEqual(ctx.default_timeout_ms, 9_000)
        self.assertFalse(ctx.retryable_by_default)
        self.assertFalse(ctx.requires_user_context)
        self.assertEqual(ctx.registration.kind, "custom_calc")

    def test_compute_tool_retry_decision_keeps_current_calc_defaults(self) -> None:
        ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )

        self.assertTrue(
            compute_tool_retry_decision(
                ctx=ctx,
                exc=MockToolExecutionError("transient", fatal=False),
            )
        )
        self.assertFalse(
            compute_tool_retry_decision(
                ctx=ctx,
                exc=MockToolExecutionError("fatal", fatal=True),
            )
        )

    def test_build_tool_end_payload_keeps_preview_and_retry_shape(self) -> None:
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        self.assertEqual(
            build_tool_end_payload(
                name="calc_eval",
                task_id="task-1",
                step_id="step-1",
                output=output,
                retry_count=0,
            ),
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "status": "done",
                "latency_ms": 12,
                "output_preview": {
                    "expression": "1+2*3",
                    "result": 7.0,
                },
                "kind": "local_calculator",
                "semantic_kind": "local_calculator",
                "supports_result_preview": True,
                "effective_result_preview_keys": ["expression", "result"],
                "retry_count": 0,
            },
        )

    def test_build_tool_end_payload_uses_registration_preview_policy_and_timeout(
        self,
    ) -> None:
        output = {
            "documents": [{"title": "Secret"}],
            "tool_kind": "custom_lookup",
        }
        registration = ToolRegistration(
            name="custom_lookup",
            kind="custom_lookup",
            label="Custom Lookup",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=False,
            runner=lambda *, tool_input, prompt, user_id: {
                "tool_input": tool_input,
                "prompt": prompt,
                "user_id": user_id,
            },
        )

        self.assertEqual(
            build_tool_end_payload(
                name="custom_lookup",
                task_id="task-1",
                step_id="step-1",
                output=output,
                retry_count=0,
                registration=registration,
            ),
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "status": "done",
                "latency_ms": 48,
                "output_preview": None,
                "kind": "custom_lookup",
                "semantic_kind": "custom_lookup",
                "supports_result_preview": False,
                "effective_result_preview_keys": [],
                "retry_count": 0,
            },
        )

    def test_build_tool_end_payload_includes_safe_output_when_effective_result_output_keys_present(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_search",
            kind="provider_retrieval",
            label="Provider Search",
            retryable_by_default=False,
            default_timeout_ms=21_000,
            requires_user_context=True,
            supports_result_preview=True,
            result_preview_keys=("documents_total",),
            result_output_keys=("documents_total", "request_id"),
            runtime_semantic_kind="provider_search",
            runner=lambda *, tool_input, prompt, user_id: {
                "tool_input": tool_input,
                "prompt": prompt,
                "user_id": user_id,
            },
        )

        payload = build_tool_end_payload(
            name="provider_search",
            task_id="task-1",
            step_id="step-1",
            output={
                "documents_total": 2,
                "request_id": "req-1",
                "raw_documents": [{"id": "doc-1"}],
            },
            retry_count=0,
            registration=registration,
        )

        self.assertEqual(
            payload["output"],
            {
                "documents_total": 2,
                "request_id": "req-1",
            },
        )
        self.assertEqual(
            payload["output_preview"],
            {
                "documents_total": 2,
            },
        )
        self.assertEqual(
            payload["effective_result_output_keys"],
            ["documents_total", "request_id"],
        )
        self.assertNotIn("raw_documents", payload["output"])

    def test_build_tool_success_and_error_meta_keep_tool_shape(self) -> None:
        tool_input = {"expression": "1+2*3"}
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        success_meta = build_tool_success_meta(
            name="calc_eval",
            tool_input=tool_input,
            output=output,
            retry_count=0,
            last_error=None,
        )
        error_meta = build_tool_error_meta(
            name="calc_eval",
            tool_input=tool_input,
            retry_count=1,
            error_message="transient",
        )

        self.assertEqual(success_meta["tool"]["name"], "calc_eval")
        self.assertEqual(success_meta["tool"]["output"], output)
        self.assertEqual(
            success_meta["tool"]["output_preview"],
            {
                "expression": "1+2*3",
                "result": 7.0,
            },
        )
        self.assertEqual(success_meta["tool"]["kind"], "local_calculator")
        self.assertEqual(success_meta["tool"]["semantic_kind"], "local_calculator")
        self.assertTrue(success_meta["tool"]["supports_result_preview"])
        self.assertEqual(
            success_meta["tool"]["effective_result_preview_keys"],
            ["expression", "result"],
        )
        self.assertEqual(success_meta["tool"]["status"], "done")
        self.assertEqual(error_meta["tool"]["name"], "calc_eval")
        self.assertEqual(error_meta["tool"]["kind"], "local_calculator")
        self.assertEqual(error_meta["tool"]["semantic_kind"], "local_calculator")
        self.assertTrue(error_meta["tool"]["supports_result_preview"])
        self.assertEqual(
            error_meta["tool"]["effective_result_preview_keys"],
            ["expression", "result"],
        )
        self.assertEqual(error_meta["tool"]["status"], "error")
        self.assertEqual(error_meta["tool"]["error"], "transient")

    def test_build_tool_success_meta_includes_effective_result_output_keys_for_real_tool(
        self,
    ) -> None:
        success_meta = build_tool_success_meta(
            name="provider_search",
            tool_input={"query": "revenue trend"},
            output={
                "documents_total": 2,
                "documents": [{"id": "doc-1"}, {"id": "doc-2"}],
                "tool_kind": "provider_retrieval",
            },
            retry_count=0,
            last_error=None,
            registration=ToolRegistration(
                name="provider_search",
                kind="provider_retrieval",
                label="Provider Search",
                retryable_by_default=False,
                default_timeout_ms=21_000,
                requires_user_context=True,
                supports_result_preview=True,
                runner=lambda *, tool_input, prompt, user_id: {
                    "documents_total": 2,
                    "tool_kind": "provider_retrieval",
                },
                result_preview_keys=("documents_total",),
                result_output_keys=("documents_total",),
                runtime_semantic_kind="provider_search",
            ),
        )

        self.assertEqual(
            success_meta["tool"]["effective_result_output_keys"],
            ["documents_total"],
        )
        self.assertEqual(success_meta["tool"]["semantic_kind"], "provider_search")
        self.assertEqual(
            success_meta["tool"]["semantic_family"],
            "knowledge_retrieval",
        )

    def test_build_tool_success_meta_redacts_http_json_raw_last_error(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_status",
            kind="provider_status",
            label="Provider Status",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
            result_preview_keys=("status",),
            result_output_keys=("status",),
        )
        base_step = build_action_step_initial_step(
            step_id="step-1",
            seq=3,
            name="provider_status",
            meta=build_action_step_initial_meta(
                name="provider_status",
                tool_input={"query": "status"},
                model="mock-gpt",
                label="tool_1",
                token_count=5,
                registration=registration,
            ),
            registration=registration,
        )

        success_meta = build_tool_success_meta(
            name="provider_status",
            tool_input={"query": "status"},
            output={"status": "ready"},
            retry_count=1,
            last_error="retry failed token=hidden api_key=hidden",
            registration=registration,
        )
        success_step = build_tool_step_success_update(
            action_step=base_step,
            name="provider_status",
            tool_input={"query": "status"},
            output={"status": "ready"},
            retry_count=1,
            token_count=7,
            last_error="retry failed token=hidden api_key=hidden",
            registration=registration,
        )

        self.assertEqual(
            success_meta["tool"]["error"],
            "retry failed [redacted] [redacted]",
        )
        self.assertEqual(
            success_step["meta"]["tool"]["error"],  # type: ignore[index]
            "retry failed [redacted] [redacted]",
        )
        combined = json.dumps(
            {"meta": success_meta, "step": success_step},
            ensure_ascii=False,
        )
        self.assertNotIn("token=hidden", combined)
        self.assertNotIn("api_key=hidden", combined)
        self.assertNotIn("hidden", combined)

    def test_build_tool_success_and_end_payload_include_result_summary_for_real_tool(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_search",
            kind="provider_retrieval",
            label="Provider Search",
            retryable_by_default=False,
            default_timeout_ms=21_000,
            requires_user_context=True,
            supports_result_preview=True,
            runner=lambda *, tool_input, prompt, user_id: {
                "documents_total": 2,
                "request_id": "req-1",
                "tool_kind": "provider_retrieval",
            },
            result_preview_keys=("documents_total",),
            result_output_keys=("documents_total", "request_id"),
            runtime_semantic_kind="provider_search",
        )

        success_meta = build_tool_success_meta(
            name="provider_search",
            tool_input={"query": "revenue trend"},
            output={
                "documents_total": 2,
                "request_id": "req-1",
                "documents": [{"id": "doc-1"}, {"id": "doc-2"}],
                "tool_kind": "provider_retrieval",
            },
            retry_count=0,
            last_error=None,
            registration=registration,
        )
        tool_end = build_tool_end_payload(
            name="provider_search",
            task_id="task-1",
            step_id="step-1",
            output={
                "documents_total": 2,
                "request_id": "req-1",
                "documents": [{"id": "doc-1"}, {"id": "doc-2"}],
                "tool_kind": "provider_retrieval",
            },
            retry_count=0,
            registration=registration,
        )

        self.assertEqual(
            success_meta["tool"]["result_summary"],
            "Retrieved 2 documents (request id req-1).",
        )
        self.assertEqual(
            tool_end["result_summary"],
            "Retrieved 2 documents (request id req-1).",
        )

    def test_build_tool_result_helpers_support_registry_provider_without_explicit_registration(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            registry=build_tool_registry(
                overrides={
                    "provider_search": ToolRegistration(
                        name="provider_search",
                        kind="provider_retrieval",
                        label="Provider Search",
                        retryable_by_default=False,
                        default_timeout_ms=21_000,
                        requires_user_context=True,
                        supports_result_preview=True,
                        runner=lambda *, tool_input, prompt, user_id: {
                            "documents_total": 2,
                            "request_id": "req-1",
                            "tool_kind": "provider_retrieval",
                        },
                        result_preview_keys=("documents_total",),
                        result_output_keys=("documents_total", "request_id"),
                        runtime_semantic_kind="provider_search",
                    )
                }
            )
        )
        output = {
            "documents_total": 2,
            "request_id": "req-1",
            "documents": [{"id": "doc-1"}, {"id": "doc-2"}],
            "tool_kind": "provider_retrieval",
        }

        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registry_provider=provider,
            ),
            {
                "documents_total": 2,
            },
        )
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registry_provider=provider,
            ),
            {
                "documents_total": 2,
                "request_id": "req-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registry_provider=provider,
            ),
            "Retrieved 2 documents (request id req-1).",
        )
        self.assertEqual(
            build_tool_observation_entry(
                name="provider_search",
                output=output,
                registry_provider=provider,
            ),
            "Provider Search: Retrieved 2 documents (request id req-1).",
        )

    def test_get_tool_effective_result_key_helpers_support_registry_provider_without_explicit_registration(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            registry=build_tool_registry(
                overrides={
                    "provider_search": ToolRegistration(
                        name="provider_search",
                        kind="provider_retrieval",
                        label="Hosted Search",
                        retryable_by_default=False,
                        default_timeout_ms=21_000,
                        requires_user_context=True,
                        supports_result_preview=True,
                        runner=lambda *, tool_input, prompt, user_id: {
                            "documents_total": 2,
                            "request_id": "req-1",
                            "tool_kind": "provider_retrieval",
                        },
                        result_preview_keys=("documents_total",),
                        result_output_keys=("documents_total", "request_id"),
                        runtime_semantic_kind="provider_search",
                    )
                }
            )
        )

        self.assertEqual(
            get_tool_effective_result_preview_keys(
                name="provider_search",
                registry_provider=provider,
            ),
            ("documents_total",),
        )
        self.assertEqual(
            get_tool_effective_result_output_keys(
                name="provider_search",
                registry_provider=provider,
            ),
            ("documents_total", "request_id"),
        )

    def test_get_tool_effective_result_key_helpers_include_documents_total_for_runtime_override_real_retrieval_tools(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_search",
            kind="provider_retrieval",
            label="Provider Search",
            retryable_by_default=False,
            default_timeout_ms=21_000,
            requires_user_context=True,
            supports_result_preview=True,
            runtime_semantic_kind="provider_search",
            runner=lambda *, tool_input, prompt, user_id: {
                "documents_total": 2,
                "documents": [{"id": "doc-1"}, {"id": "doc-2"}],
                "tool_kind": "provider_retrieval",
            },
        )

        self.assertEqual(
            get_tool_effective_result_preview_keys(
                name="provider_search",
                registration=registration,
            ),
            ("documents_total", "hit_count", "knowledge_base_id"),
        )
        self.assertEqual(
            get_tool_effective_result_output_keys(
                name="provider_search",
                registration=registration,
            ),
            ("documents_total", "hit_count", "knowledge_base_id", "request_id"),
        )

    def test_build_tool_result_helpers_fall_back_to_documents_total_for_runtime_override_real_retrieval_tools(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_search",
            kind="provider_retrieval",
            label="Provider Search",
            retryable_by_default=False,
            default_timeout_ms=21_000,
            requires_user_context=True,
            supports_result_preview=True,
            runtime_semantic_kind="provider_search",
            runner=lambda *, tool_input, prompt, user_id: {
                "documents_total": 2,
                "documents": [{"id": "doc-1"}, {"id": "doc-2"}],
                "request_id": "req-1",
                "tool_kind": "provider_retrieval",
            },
        )
        output = {
            "documents_total": 2,
            "documents": [{"id": "doc-1"}, {"id": "doc-2"}],
            "request_id": "req-1",
            "tool_kind": "provider_retrieval",
        }

        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            {
                "documents_total": 2,
            },
        )
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            {
                "documents_total": 2,
                "request_id": "req-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            "Retrieved 2 documents (request id req-1).",
        )
        self.assertEqual(
            build_tool_observation_entry(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            "Provider Search: Retrieved 2 documents (request id req-1).",
        )

    def test_build_tool_result_helpers_normalize_http_json_items_alias_for_raw_output(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_search",
            kind="provider_retrieval",
            label="Provider Search",
            retryable_by_default=False,
            default_timeout_ms=21_000,
            requires_user_context=True,
            supports_result_preview=True,
            runtime_semantic_kind="provider_search",
            execution_kind="http_json",
            result_preview_keys=("documents_total",),
            result_output_keys=("documents_total", "request_id"),
            runner=lambda *, tool_input, prompt, user_id: {
                "items": [{"id": "doc-1"}, {"id": "doc-2"}],
                "request_id": "req-items-raw-1",
            },
        )
        output = {
            "items": [{"id": "doc-1"}, {"id": "doc-2"}],
            "request_id": "req-items-raw-1",
        }

        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            {
                "documents_total": 2,
            },
        )
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            {
                "documents_total": 2,
                "request_id": "req-items-raw-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            "Retrieved 2 documents (request id req-items-raw-1).",
        )
        self.assertEqual(
            build_tool_observation_entry(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            "Provider Search: Retrieved 2 documents (request id req-items-raw-1).",
        )

    def test_build_tool_result_helpers_normalize_http_json_matches_when_raw_count_is_invalid(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_search",
            kind="provider_retrieval",
            label="Provider Search",
            retryable_by_default=False,
            default_timeout_ms=21_000,
            requires_user_context=True,
            supports_result_preview=True,
            runtime_semantic_kind="provider_search",
            execution_kind="http_json",
            result_preview_keys=("hit_count", "knowledge_base_id"),
            result_output_keys=("hit_count", "knowledge_base_id", "request_id"),
            runner=lambda *, tool_input, prompt, user_id: {
                "hit_count": "unknown",
                "matches": [{"id": "vec-1"}, {"id": "vec-2"}],
                "knowledge_base_id": "provider-kb",
                "request_id": "req-matches-raw-1",
            },
        )
        output = {
            "hit_count": "unknown",
            "matches": [{"id": "vec-1"}, {"id": "vec-2"}],
            "knowledge_base_id": "provider-kb",
            "request_id": "req-matches-raw-1",
        }

        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            {
                "hit_count": 2,
                "knowledge_base_id": "provider-kb",
            },
        )
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            {
                "hit_count": 2,
                "knowledge_base_id": "provider-kb",
                "request_id": "req-matches-raw-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            "Retrieved 2 hits (request id req-matches-raw-1).",
        )
        self.assertEqual(
            build_tool_observation_entry(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            "Provider Search: Retrieved 2 hits (request id req-matches-raw-1).",
        )

    def test_build_tool_result_helpers_do_not_infer_http_json_aliases_for_non_http_json_raw_output(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_search",
            kind="provider_retrieval",
            label="Provider Search",
            retryable_by_default=False,
            default_timeout_ms=21_000,
            requires_user_context=True,
            supports_result_preview=True,
            runtime_semantic_kind="provider_search",
            result_preview_keys=("documents_total",),
            result_output_keys=("documents_total", "request_id"),
            runner=lambda *, tool_input, prompt, user_id: {
                "items": [{"id": "doc-1"}, {"id": "doc-2"}],
                "request_id": "req-items-raw-1",
            },
        )
        output = {
            "items": [{"id": "doc-1"}, {"id": "doc-2"}],
            "request_id": "req-items-raw-1",
        }

        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            {},
        )
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            {
                "request_id": "req-items-raw-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            "Provider Search output - request_id=req-items-raw-1.",
        )

    def test_build_tool_result_helpers_preserve_request_id_for_runtime_override_real_retrieval_hit_projection(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_search",
            kind="provider_retrieval",
            label="Provider Search",
            retryable_by_default=False,
            default_timeout_ms=21_000,
            requires_user_context=True,
            supports_result_preview=True,
            runtime_semantic_kind="provider_search",
            runner=lambda *, tool_input, prompt, user_id: {
                "hit_count": 2,
                "knowledge_base_id": "provider-kb",
                "request_id": "req-1",
                "tool_kind": "provider_retrieval",
            },
        )
        output = {
            "hit_count": 2,
            "knowledge_base_id": "provider-kb",
            "request_id": "req-1",
            "tool_kind": "provider_retrieval",
        }

        self.assertEqual(
            build_tool_result_preview(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            {
                "hit_count": 2,
                "knowledge_base_id": "provider-kb",
            },
        )
        self.assertEqual(
            build_tool_result_output(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            {
                "hit_count": 2,
                "knowledge_base_id": "provider-kb",
                "request_id": "req-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            "Retrieved 2 hits (request id req-1).",
        )
        self.assertEqual(
            build_tool_observation_entry(
                name="provider_search",
                output=output,
                registration=registration,
            ),
            "Provider Search: Retrieved 2 hits (request id req-1).",
        )

    def test_get_tool_effective_result_key_helpers_preserve_request_id_for_http_json_provider_calc_without_explicit_output_keys(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_math",
            kind="provider_calc",
            label="Provider Math",
            retryable_by_default=False,
            default_timeout_ms=21_000,
            requires_user_context=True,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {
                "result": 7,
                "request_id": "req-calc-1",
                "tool_kind": "provider_calc",
            },
        )

        self.assertEqual(
            get_tool_effective_result_preview_keys(
                name="provider_math",
                registration=registration,
            ),
            ("expression", "result"),
        )
        self.assertEqual(
            get_tool_effective_result_output_keys(
                name="provider_math",
                registration=registration,
            ),
            ("expression", "result", "request_id"),
        )

    def test_build_tool_result_helpers_preserve_request_id_for_http_json_provider_calc_without_explicit_output_keys(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_math",
            kind="provider_calc",
            label="Provider Math",
            retryable_by_default=False,
            default_timeout_ms=21_000,
            requires_user_context=True,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {
                "result": 7,
                "request_id": "req-calc-1",
                "tool_kind": "provider_calc",
            },
        )
        output = {
            "result": 7,
            "request_id": "req-calc-1",
            "tool_kind": "provider_calc",
        }

        self.assertEqual(
            build_tool_result_preview(
                name="provider_math",
                output=output,
                registration=registration,
            ),
            {
                "result": 7,
            },
        )
        self.assertEqual(
            build_tool_result_output(
                name="provider_math",
                output=output,
                registration=registration,
            ),
            {
                "result": 7,
                "request_id": "req-calc-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_math",
                output=output,
                registration=registration,
            ),
            "Calculated result = 7 (request id req-calc-1).",
        )
        self.assertEqual(
            build_tool_observation_entry(
                name="provider_math",
                output=output,
                registration=registration,
            ),
            "Provider Math: Calculated result = 7 (request id req-calc-1).",
        )

    def test_build_tool_result_helpers_drop_unsafe_request_id_for_http_json_provider_calc(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_math",
            kind="provider_calc",
            label="Provider Math",
            retryable_by_default=False,
            default_timeout_ms=21_000,
            requires_user_context=True,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {
                "result": 7,
                "request_id": "Bearer secret-token",
                "tool_kind": "provider_calc",
            },
        )
        output = {
            "result": 7,
            "request_id": "Bearer secret-token",
            "tool_kind": "provider_calc",
        }

        self.assertEqual(
            build_tool_result_output(
                name="provider_math",
                output=output,
                registration=registration,
            ),
            {
                "result": 7,
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="provider_math",
                output=output,
                registration=registration,
            ),
            "Calculated result = 7.",
        )
        self.assertEqual(
            build_tool_observation_entry(
                name="provider_math",
                output=output,
                registration=registration,
            ),
            "Provider Math: Calculated result = 7.",
        )

    def test_build_tool_start_and_error_payload_keep_current_shape(self) -> None:
        self.assertEqual(
            build_tool_start_payload(
                task_id="task-1",
                step_id="step-1",
                name="calc_eval",
                tool_input={"expression": "1+2*3"},
                retry_count=0,
            ),
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "name": "calc_eval",
                "display_name": "Calculator",
                "input": {"expression": "1+2*3"},
                "kind": "local_calculator",
                "semantic_kind": "local_calculator",
                "supports_result_preview": True,
                "effective_result_preview_keys": ["expression", "result"],
                "retry_count": 0,
            },
        )
        self.assertEqual(
            build_tool_error_payload(
                name="calc_eval",
                task_id="task-1",
                step_id="step-1",
                error_message="transient",
                retry_count=1,
            ),
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "status": "error",
                "latency_ms": 12,
                "output_preview": {"error": "transient"},
                "kind": "local_calculator",
                "semantic_kind": "local_calculator",
                "supports_result_preview": True,
                "effective_result_preview_keys": ["expression", "result"],
                "retry_count": 1,
                "error": "transient",
            },
        )

    def test_build_tool_start_payload_supports_registry_provider_without_explicit_registration(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            registry=build_tool_registry(
                overrides={
                    "provider_search": ToolRegistration(
                        name="provider_search",
                        kind="provider_retrieval",
                        label="Provider Search",
                        retryable_by_default=False,
                        default_timeout_ms=21_000,
                        requires_user_context=True,
                        supports_result_preview=True,
                        runner=lambda *, tool_input, prompt, user_id: {
                            "documents_total": 2,
                            "tool_kind": "provider_retrieval",
                        },
                        result_preview_keys=("documents_total",),
                        result_output_keys=("documents_total",),
                        runtime_semantic_kind="provider_search",
                    )
                }
            )
        )

        self.assertEqual(
            build_tool_start_payload(
                task_id="task-1",
                step_id="step-1",
                name="provider_search",
                tool_input={"query": "revenue trend"},
                retry_count=0,
                registry_provider=provider,
            ),
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "name": "provider_search",
                "display_name": "Provider Search",
                "input": {"query": "revenue trend"},
                "kind": "provider_retrieval",
                "semantic_kind": "provider_search",
                "semantic_family": "knowledge_retrieval",
                "supports_result_preview": True,
                "effective_result_preview_keys": ["documents_total"],
                "effective_result_output_keys": ["documents_total"],
                "retry_count": 0,
            },
        )

    def test_build_tool_start_payload_includes_http_json_execution_summary(
        self,
    ) -> None:
        provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_provider_source="analytics_suite",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "analytics_suite": {
                            "provider": "default",
                            "profile": "default",
                            "disabled_tool_names": [
                                "task_plan",
                                "task_retrieve",
                                "calc_eval",
                            ],
                            "extra_tools": {
                                "provider_search": {
                                    "template": "task_retrieve",
                                    "label": "Provider Search",
                                    "kind": "provider_retrieval",
                                    "runtime_semantic_kind": "provider_search",
                                    "execution": {
                                        "kind": "http_json",
                                        "url": "https://provider.example/search?debug=1",
                                        "method": "POST",
                                        "headers": {"X-Trace-Token": "trace-demo"},
                                        "query_params": {"q": "$query"},
                                        "json_body": {"query": "$query", "limit": "$top_k"},
                                        "response_path": "$.data",
                                        "result_fields": {
                                            "documents_total": "$.meta.total",
                                            "request_id": "$.meta.request_id",
                                        },
                                    },
                                    "result_preview_keys": ["documents_total"],
                                    "result_output_keys": ["documents_total", "request_id"],
                                }
                            },
                        }
                    }
                ),
            )
        )

        self.assertEqual(
            build_tool_start_payload(
                task_id="task-1",
                step_id="step-1",
                name="provider_search",
                tool_input={"query": "revenue trend", "top_k": 2},
                retry_count=0,
                registry_provider=provider,
            ),
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "name": "provider_search",
                "display_name": "Provider Search",
                "input": {"query": "revenue trend", "top_k": 2},
                "kind": "provider_retrieval",
                "semantic_kind": "provider_search",
                "execution_kind": "http_json",
                "execution_summary": {
                    "method": "POST",
                    "url_origin": "https://provider.example",
                    "url_path": "/search",
                    "header_count": 1,
                    "query_param_count": 1,
                    "json_body_field_count": 2,
                    "response_path": "$.data",
                    "result_field_names": ["documents_total", "request_id"],
                },
                "semantic_family": "knowledge_retrieval",
                "supports_result_preview": True,
                "effective_result_preview_keys": ["documents_total"],
                "effective_result_output_keys": ["documents_total", "request_id"],
                "retry_count": 0,
            },
        )

    def test_build_tool_start_and_action_meta_redact_http_json_sensitive_tool_input(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_search",
            kind="provider_retrieval",
            label="Provider Search",
            retryable_by_default=False,
            default_timeout_ms=21_000,
            requires_user_context=True,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {
                "documents_total": 1,
                "tool_kind": "provider_retrieval",
            },
            result_preview_keys=("documents_total",),
            result_output_keys=("documents_total",),
            runtime_semantic_kind="provider_search",
        )
        tool_input = {
            "query": "revenue trend token=hidden",
            "access_token": "hidden",
            "filters": {
                "client_secret": "hidden",
                "region": "us",
            },
            "headers": [
                {
                    "Authorization": "Bearer hidden",
                    "label": "primary token=hidden",
                }
            ],
        }

        start_payload = build_tool_start_payload(
            task_id="task-1",
            step_id="step-1",
            name="provider_search",
            tool_input=tool_input,
            retry_count=0,
            registration=registration,
        )
        action_meta = build_action_step_initial_meta(
            name="provider_search",
            tool_input=tool_input,
            model="mock-gpt",
            label="tool_2",
            token_count=5,
            registration=registration,
        )
        success_meta = build_tool_success_meta(
            name="provider_search",
            tool_input=tool_input,
            output={"documents_total": 1},
            retry_count=0,
            last_error=None,
            registration=registration,
        )
        error_meta = build_tool_error_meta(
            name="provider_search",
            tool_input=tool_input,
            retry_count=0,
            error_message="upstream failed",
            registration=registration,
        )

        expected_safe_input = {
            "query": "revenue trend token=[redacted]",
            "access_token": "[redacted]",
            "filters": {
                "client_secret": "[redacted]",
                "region": "us",
            },
            "headers": [
                {
                    "Authorization": "[redacted]",
                    "label": "primary token=[redacted]",
                }
            ],
        }
        self.assertEqual(
            start_payload["input"],
            expected_safe_input,
        )
        self.assertEqual(action_meta["tool"]["input"], start_payload["input"])  # type: ignore[index]
        self.assertEqual(success_meta["tool"]["input"], expected_safe_input)  # type: ignore[index]
        self.assertEqual(error_meta["tool"]["input"], expected_safe_input)  # type: ignore[index]
        combined = json.dumps(
            {
                "start": start_payload,
                "meta": action_meta,
                "success": success_meta,
                "error": error_meta,
            },
            ensure_ascii=False,
        )
        self.assertNotIn("token=hidden", combined)
        self.assertNotIn("Bearer hidden", combined)
        self.assertNotIn("client_secret\": \"hidden", combined)
        self.assertNotIn("access_token\": \"hidden", combined)

    def test_build_tool_start_and_error_payload_include_execution_diagnostics_for_invalid_real_tool_execution(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_overrides_json=json.dumps(
                    {
                        "calc_eval": {
                            "kind": "provider_calc",
                            "label": "Provider Calculator",
                            "execution": {
                                "kind": "unsupported_transport",
                            },
                        }
                    }
                ),
                tool_registry_extra_tools_json=None,
                tool_registry_profile="default",
                tool_registry_provider_sources_json=json.dumps({}),
            )
        )

        self.assertEqual(
            build_tool_start_payload(
                task_id="task-1",
                step_id="step-1",
                name="calc_eval",
                tool_input={"expression": "1+2*3"},
                retry_count=0,
                registry_provider=registry_provider,
            ),
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "name": "calc_eval",
                "display_name": "Provider Calculator",
                "input": {"expression": "1+2*3"},
                "kind": "provider_calc",
                "semantic_kind": "local_calculator",
                "execution_kind": "unsupported_transport",
                "execution_diagnostics": [
                    "unsupported tool execution kind unsupported_transport",
                ],
                "supports_result_preview": True,
                "effective_result_preview_keys": ["expression", "result"],
                "effective_result_output_keys": ["expression", "result"],
                "retry_count": 0,
            },
        )
        self.assertEqual(
            build_tool_error_payload(
                name="calc_eval",
                task_id="task-1",
                step_id="step-1",
                error_message="Unsupported tool execution kind: unsupported_transport",
                retry_count=0,
                registry_provider=registry_provider,
            ),
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "status": "error",
                "latency_ms": 12,
                "output_preview": {
                    "error": "Unsupported tool execution kind: unsupported_transport",
                },
                "kind": "provider_calc",
                "semantic_kind": "local_calculator",
                "execution_kind": "unsupported_transport",
                "execution_diagnostics": [
                    "unsupported tool execution kind unsupported_transport",
                ],
                "supports_result_preview": True,
                "effective_result_preview_keys": ["expression", "result"],
                "effective_result_output_keys": ["expression", "result"],
                "retry_count": 0,
                "error": "Unsupported tool execution kind: unsupported_transport",
            },
        )

    def test_build_tool_runtime_semantics_meta_redacts_sensitive_execution_diagnostics(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_search",
            kind="provider_retrieval",
            label="Provider Search",
            retryable_by_default=False,
            default_timeout_ms=21_000,
            requires_user_context=True,
            supports_result_preview=True,
            execution_kind="http_json",
            execution_diagnostics=(
                "unsupported tool execution kind api_key=hidden",
                "http_json execution query_params.access_token must be safe",
            ),
            runner=lambda *, tool_input, prompt, user_id: {
                "documents_total": 1,
            },
            result_preview_keys=("documents_total",),
            result_output_keys=("documents_total",),
            runtime_semantic_kind="provider_search",
        )

        start_payload = build_tool_start_payload(
            task_id="task-1",
            step_id="step-1",
            name="provider_search",
            tool_input={"query": "revenue trend"},
            retry_count=0,
            registration=registration,
        )
        action_meta = build_action_step_initial_meta(
            name="provider_search",
            tool_input={"query": "revenue trend"},
            model="mock-gpt",
            label="tool_2",
            token_count=5,
            registration=registration,
        )

        self.assertEqual(
            start_payload["execution_diagnostics"],
            [
                "unsupported tool execution kind [redacted]",
                "http_json execution [redacted] must be safe",
            ],
        )
        self.assertEqual(
            action_meta["tool"]["execution_diagnostics"],  # type: ignore[index]
            start_payload["execution_diagnostics"],
        )
        combined = json.dumps(
            {"start": start_payload, "action_meta": action_meta},
            ensure_ascii=False,
        )
        self.assertNotIn("api_key=hidden", combined)
        self.assertNotIn("access_token", combined)

    def test_build_tool_runtime_semantics_meta_redacts_wrapped_execution_diagnostics(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_search",
            kind="provider_retrieval",
            label="Provider Search",
            retryable_by_default=False,
            default_timeout_ms=21_000,
            requires_user_context=True,
            supports_result_preview=True,
            execution_kind="http_json",
            execution_diagnostics=(
                UserString("unsupported tool execution kind api_key=hidden"),
                UserString("unsupported tool execution kind api_key=hidden"),
                UserString(
                    "http_json execution query_params.access_token must be safe"
                ),
            ),
            runner=lambda *, tool_input, prompt, user_id: {
                "documents_total": 1,
            },
            result_preview_keys=("documents_total",),
            result_output_keys=("documents_total",),
            runtime_semantic_kind="provider_search",
        )

        start_payload = build_tool_start_payload(
            task_id="task-1",
            step_id="step-1",
            name="provider_search",
            tool_input={"query": "revenue trend"},
            retry_count=0,
            registration=registration,
        )
        action_meta = build_action_step_initial_meta(
            name="provider_search",
            tool_input={"query": "revenue trend"},
            model="mock-gpt",
            label="tool_2",
            token_count=5,
            registration=registration,
        )

        self.assertEqual(
            start_payload["execution_diagnostics"],
            [
                "unsupported tool execution kind [redacted]",
                "http_json execution [redacted] must be safe",
            ],
        )
        self.assertEqual(
            action_meta["tool"]["execution_diagnostics"],  # type: ignore[index]
            start_payload["execution_diagnostics"],
        )
        combined = json.dumps(
            {"start": start_payload, "action_meta": action_meta},
            ensure_ascii=False,
        )
        self.assertNotIn("api_key=hidden", combined)
        self.assertNotIn("access_token", combined)

    def test_build_tool_runtime_semantics_meta_infers_label_only_real_tool_family(
        self,
    ) -> None:
        registrations = {
            "hosted_math_gateway": ToolRegistration(
                name="hosted_math_gateway",
                kind="",
                label="Hosted Math",
                retryable_by_default=False,
                default_timeout_ms=12_000,
                requires_user_context=False,
                supports_result_preview=True,
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {},
            ),
            "hosted_search_gateway": ToolRegistration(
                name="hosted_search_gateway",
                kind="",
                label="Hosted Search",
                retryable_by_default=False,
                default_timeout_ms=12_000,
                requires_user_context=False,
                supports_result_preview=True,
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {},
            ),
            "hosted_planner_gateway": ToolRegistration(
                name="hosted_planner_gateway",
                kind="",
                label="Hosted Planner",
                retryable_by_default=False,
                default_timeout_ms=12_000,
                requires_user_context=False,
                supports_result_preview=True,
                execution_kind="http_json",
                runner=lambda *, tool_input, prompt, user_id: {},
            ),
        }

        math_meta = build_tool_runtime_semantics_meta(
            name="hosted_math_gateway",
            registration=registrations["hosted_math_gateway"],
        )
        search_meta = build_tool_runtime_semantics_meta(
            name="hosted_search_gateway",
            registration=registrations["hosted_search_gateway"],
        )
        planner_meta = build_tool_runtime_semantics_meta(
            name="hosted_planner_gateway",
            registration=registrations["hosted_planner_gateway"],
        )

        self.assertEqual(math_meta["semantic_kind"], "hosted_math_gateway")
        self.assertEqual(math_meta["semantic_family"], "local_calculator")
        self.assertEqual(math_meta["effective_result_preview_keys"], ["expression", "result"])
        self.assertEqual(
            math_meta["effective_result_output_keys"],
            ["expression", "result", "request_id"],
        )
        self.assertEqual(search_meta["semantic_kind"], "hosted_search_gateway")
        self.assertEqual(search_meta["semantic_family"], "knowledge_retrieval")
        self.assertEqual(
            search_meta["effective_result_preview_keys"],
            ["documents_total", "hit_count", "knowledge_base_id"],
        )
        self.assertEqual(
            search_meta["effective_result_output_keys"],
            ["documents_total", "hit_count", "knowledge_base_id", "request_id"],
        )
        self.assertEqual(planner_meta["semantic_kind"], "hosted_planner_gateway")
        self.assertEqual(planner_meta["semantic_family"], "task_planner")
        self.assertEqual(planner_meta["effective_result_preview_keys"], ["plan", "steps"])
        self.assertEqual(planner_meta["effective_result_output_keys"], ["plan", "steps"])

    def test_build_tool_runtime_semantics_meta_accepts_kind_string_wrapper(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="typed_gateway",
            kind=UserString("provider_retrieval"),
            label="Typed Gateway",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
        )

        meta = build_tool_runtime_semantics_meta(
            name="typed_gateway",
            registration=registration,
        )

        self.assertEqual(meta["semantic_kind"], "typed_gateway")
        self.assertEqual(meta["semantic_family"], "knowledge_retrieval")

    def test_build_tool_runtime_semantics_meta_accepts_runtime_kind_string_wrapper(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_gateway",
            kind="provider_retrieval",
            label="Provider Gateway",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
            runtime_semantic_kind=UserString("provider_search"),
        )

        meta = build_tool_runtime_semantics_meta(
            name="provider_gateway",
            registration=registration,
        )

        self.assertEqual(meta["semantic_kind"], "provider_search")
        self.assertEqual(meta["semantic_family"], "knowledge_retrieval")

    def test_label_only_real_retrieval_with_explicit_preview_keys_infers_output_diagnostic_keys(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="hosted_search_gateway",
            kind=None,
            label="Hosted Search",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
            result_preview_keys=("documents_total",),
        )
        output = {
            "documents_total": 2,
            "knowledge_base_id": "hosted-kb",
            "request_id": "req-hosted-1",
            "documents": [{"id": "doc-1"}, {"id": "doc-2"}],
        }

        self.assertEqual(
            get_tool_effective_result_preview_keys(
                name="hosted_search_gateway",
                registration=registration,
            ),
            ("documents_total",),
        )
        self.assertEqual(
            get_tool_effective_result_output_keys(
                name="hosted_search_gateway",
                registration=registration,
            ),
            ("documents_total", "knowledge_base_id", "request_id"),
        )
        self.assertEqual(
            build_tool_result_output(
                name="hosted_search_gateway",
                output=output,
                registration=registration,
            ),
            {
                "documents_total": 2,
                "knowledge_base_id": "hosted-kb",
                "request_id": "req-hosted-1",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="hosted_search_gateway",
                output=output,
                registration=registration,
            ),
            "Retrieved 2 documents from hosted-kb (request id req-hosted-1).",
        )

    def test_label_only_real_retrieval_preview_only_output_keys_filter_sensitive_legacy_keys(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="hosted_search_gateway",
            kind=None,
            label="Hosted Search",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
            result_preview_keys=("documents_total", "access_token"),
        )

        self.assertEqual(
            get_tool_effective_result_preview_keys(
                name="hosted_search_gateway",
                registration=registration,
            ),
            ("documents_total",),
        )
        self.assertEqual(
            get_tool_effective_result_output_keys(
                name="hosted_search_gateway",
                registration=registration,
            ),
            ("documents_total", "knowledge_base_id", "request_id"),
        )
        self.assertEqual(
            build_tool_runtime_semantics_meta(
                name="hosted_search_gateway",
                registration=registration,
            ),
            {
                "kind": None,
                "semantic_kind": "hosted_search_gateway",
                "execution_kind": "http_json",
                "semantic_family": "knowledge_retrieval",
                "supports_result_preview": True,
                "effective_result_preview_keys": ["documents_total"],
                "effective_result_output_keys": [
                    "documents_total",
                    "knowledge_base_id",
                    "request_id",
                ],
            },
        )

    def test_label_only_real_retrieval_result_key_wrappers_filter_sensitive_keys(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="hosted_search_gateway",
            kind=None,
            label="Hosted Search",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
            result_preview_keys=UserList(
                [UserString("documents_total"), UserString("access_token")]
            ),
            result_output_keys=UserList(
                [
                    UserString("documents_total"),
                    UserString("access_token"),
                    UserString("request_id"),
                ]
            ),
        )
        output = {
            "documents_total": 2,
            "access_token": "secret-token",
            "request_id": "req-hosted-1",
        }

        self.assertEqual(
            get_tool_effective_result_preview_keys(
                name="hosted_search_gateway",
                registration=registration,
            ),
            ("documents_total",),
        )
        self.assertEqual(
            get_tool_effective_result_output_keys(
                name="hosted_search_gateway",
                registration=registration,
            ),
            ("documents_total", "request_id"),
        )
        self.assertEqual(
            build_tool_result_preview(
                name="hosted_search_gateway",
                output=output,
                registration=registration,
            ),
            {"documents_total": 2},
        )
        self.assertEqual(
            build_tool_result_output(
                name="hosted_search_gateway",
                output=output,
                registration=registration,
            ),
            {
                "documents_total": 2,
                "request_id": "req-hosted-1",
            },
        )
        meta = build_tool_runtime_semantics_meta(
            name="hosted_search_gateway",
            registration=registration,
        )
        self.assertEqual(meta["effective_result_preview_keys"], ["documents_total"])
        self.assertEqual(
            meta["effective_result_output_keys"],
            ["documents_total", "request_id"],
        )
        self.assertNotIn("access_token", json.dumps(meta, ensure_ascii=False))

    def test_label_only_real_retrieval_sensitive_only_result_key_wrappers_do_not_fallback(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="hosted_search_gateway",
            kind=None,
            label="Hosted Search",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
            result_preview_keys=UserList([UserString("access_token")]),
            result_output_keys=UserList([UserString("access_token")]),
        )
        output = {
            "documents_total": 2,
            "knowledge_base_id": "hosted-kb",
            "access_token": "secret-token",
            "request_id": "req-hosted-1",
        }

        self.assertEqual(
            get_tool_effective_result_preview_keys(
                name="hosted_search_gateway",
                registration=registration,
            ),
            (),
        )
        self.assertEqual(
            get_tool_effective_result_output_keys(
                name="hosted_search_gateway",
                registration=registration,
            ),
            (),
        )
        self.assertEqual(
            build_tool_result_preview(
                name="hosted_search_gateway",
                output=output,
                registration=registration,
            ),
            {},
        )
        self.assertEqual(
            build_tool_result_output(
                name="hosted_search_gateway",
                output=output,
                registration=registration,
            ),
            {},
        )

    def test_label_only_real_retrieval_explicit_output_keys_filter_sensitive_legacy_keys(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="hosted_search_gateway",
            kind=None,
            label="Hosted Search",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
            result_preview_keys=("documents_total",),
            result_output_keys=("documents_total", "access_token", "request_id"),
        )
        output = {
            "documents_total": 2,
            "access_token": "secret-token",
            "request_id": "req-hosted-1",
        }

        self.assertEqual(
            get_tool_effective_result_output_keys(
                name="hosted_search_gateway",
                registration=registration,
            ),
            ("documents_total", "request_id"),
        )
        self.assertEqual(
            build_tool_result_output(
                name="hosted_search_gateway",
                output=output,
                registration=registration,
            ),
            {
                "documents_total": 2,
                "request_id": "req-hosted-1",
            },
        )
        self.assertEqual(
            build_tool_runtime_semantics_meta(
                name="hosted_search_gateway",
                registration=registration,
            )["effective_result_output_keys"],
            ["documents_total", "request_id"],
        )

    def test_label_only_real_retrieval_sensitive_only_preview_keys_do_not_fallback_to_default_projection(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="hosted_search_gateway",
            kind=None,
            label="Hosted Search",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
            result_preview_keys=("access_token",),
        )
        output = {
            "documents_total": 2,
            "knowledge_base_id": "hosted-kb",
            "access_token": "secret-token",
            "request_id": "req-hosted-1",
        }

        self.assertEqual(
            get_tool_effective_result_preview_keys(
                name="hosted_search_gateway",
                registration=registration,
            ),
            (),
        )
        self.assertEqual(
            get_tool_effective_result_output_keys(
                name="hosted_search_gateway",
                registration=registration,
            ),
            (),
        )
        self.assertEqual(
            build_tool_result_preview(
                name="hosted_search_gateway",
                output=output,
                registration=registration,
            ),
            {},
        )
        self.assertEqual(
            build_tool_result_output(
                name="hosted_search_gateway",
                output=output,
                registration=registration,
            ),
            {},
        )

    def test_label_only_real_retrieval_sensitive_only_output_keys_do_not_fallback_to_default_projection(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="hosted_search_gateway",
            kind=None,
            label="Hosted Search",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
            result_preview_keys=("documents_total",),
            result_output_keys=("access_token",),
        )
        output = {
            "documents_total": 2,
            "knowledge_base_id": "hosted-kb",
            "access_token": "secret-token",
            "request_id": "req-hosted-1",
        }

        self.assertEqual(
            get_tool_effective_result_output_keys(
                name="hosted_search_gateway",
                registration=registration,
            ),
            (),
        )
        self.assertEqual(
            build_tool_result_output(
                name="hosted_search_gateway",
                output=output,
                registration=registration,
            ),
            {},
        )
        success_meta = build_tool_success_meta(
            name="hosted_search_gateway",
            tool_input={"query": "quarterly revenue"},
            output=output,
            retry_count=0,
            last_error=None,
            registration=registration,
        )
        self.assertEqual(success_meta["tool"]["output"], {})
        self.assertNotIn("result_summary", success_meta["tool"])

    def test_label_only_real_http_json_output_normalization_does_not_emit_null_tool_kind(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="hosted_search_gateway",
            kind=None,
            label="Hosted Search",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
        )

        output = normalize_tool_output_for_registration(
            output={
                "documents_total": 2,
                "access_token": "secret-token",
                "message": "gateway token=hidden",
            },
            registration=registration,
        )

        self.assertEqual(output["documents_total"], 2)
        self.assertEqual(output["access_token"], "[redacted]")
        self.assertEqual(output["message"], "gateway token=[redacted]")
        self.assertNotIn("tool_kind", output)

    def test_label_only_real_planner_with_explicit_preview_keys_infers_output_keys(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="hosted_planner_gateway",
            kind=None,
            label="Hosted Planner",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
            result_preview_keys=("plan",),
        )
        output = {
            "plan": "Analyze request -> Synthesize final answer",
            "steps": ["Analyze request", "Synthesize final answer"],
            "debug": "ignored",
        }

        self.assertEqual(
            get_tool_effective_result_preview_keys(
                name="hosted_planner_gateway",
                registration=registration,
            ),
            ("plan",),
        )
        self.assertEqual(
            get_tool_effective_result_output_keys(
                name="hosted_planner_gateway",
                registration=registration,
            ),
            ("plan",),
        )
        self.assertEqual(
            build_tool_result_output(
                name="hosted_planner_gateway",
                output=output,
                registration=registration,
            ),
            {
                "plan": "Analyze request -> Synthesize final answer",
            },
        )
        self.assertEqual(
            build_tool_result_summary(
                name="hosted_planner_gateway",
                output=output,
                registration=registration,
            ),
            "Planned steps - Analyze request -> Synthesize final answer.",
        )

    def test_preflight_tool_details_infer_label_only_real_tool_family(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            registry={
                "hosted_math_gateway": ToolRegistration(
                    name="hosted_math_gateway",
                    kind="",
                    label="Hosted Math",
                    retryable_by_default=False,
                    default_timeout_ms=12_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    execution_kind="http_json",
                    runner=lambda *, tool_input, prompt, user_id: {},
                ),
                "hosted_search_gateway": ToolRegistration(
                    name="hosted_search_gateway",
                    kind="",
                    label="Hosted Search",
                    retryable_by_default=False,
                    default_timeout_ms=12_000,
                    requires_user_context=False,
                    supports_result_preview=True,
                    execution_kind="http_json",
                    runner=lambda *, tool_input, prompt, user_id: {},
                ),
            }
        )

        details = {
            item["name"]: item
            for item in build_configured_tool_registry_provider_preflight_tool_details(
                provider=provider
            )
        }

        self.assertEqual(
            details["hosted_math_gateway"]["semantic_kind"],
            "hosted_math_gateway",
        )
        self.assertEqual(
            details["hosted_math_gateway"]["semantic_family"],
            "local_calculator",
        )
        self.assertEqual(
            details["hosted_math_gateway"]["effective_result_preview_keys"],
            ("expression", "result"),
        )
        self.assertEqual(
            details["hosted_math_gateway"]["effective_result_output_keys"],
            ("expression", "result", "request_id"),
        )
        self.assertEqual(
            details["hosted_search_gateway"]["semantic_kind"],
            "hosted_search_gateway",
        )
        self.assertEqual(
            details["hosted_search_gateway"]["semantic_family"],
            "knowledge_retrieval",
        )
        self.assertEqual(
            details["hosted_search_gateway"]["effective_result_preview_keys"],
            ("documents_total", "hit_count", "knowledge_base_id"),
        )
        self.assertEqual(
            details["hosted_search_gateway"]["effective_result_output_keys"],
            ("documents_total", "hit_count", "knowledge_base_id", "request_id"),
        )

    def test_build_tool_runtime_semantics_meta_redacts_sensitive_execution_summary(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_search",
            kind="provider_retrieval",
            label="Provider Search",
            retryable_by_default=False,
            default_timeout_ms=21_000,
            requires_user_context=True,
            supports_result_preview=True,
            execution_kind="http_json",
            execution_summary={
                "method": "GET",
                "url_origin": "https://provider.example",
                "url_path": "/v1/token=hidden/api_key/secret/search",
                "response_path": "$.data.access_token",
                "result_field_names": ["documents_total", "access_token"],
            },
            runner=lambda *, tool_input, prompt, user_id: {
                "documents_total": 1,
            },
            result_preview_keys=("documents_total",),
            result_output_keys=("documents_total",),
            runtime_semantic_kind="provider_search",
        )

        start_payload = build_tool_start_payload(
            task_id="task-1",
            step_id="step-1",
            name="provider_search",
            tool_input={"query": "revenue trend"},
            retry_count=0,
            registration=registration,
        )
        action_meta = build_action_step_initial_meta(
            name="provider_search",
            tool_input={"query": "revenue trend"},
            model="mock-gpt",
            label="tool_2",
            token_count=5,
            registration=registration,
        )

        expected_summary = {
            "method": "GET",
            "url_origin": "https://provider.example",
            "url_path": "/v1/[redacted]/[redacted]/[redacted]/search",
            "response_path": "$.data.[redacted]",
            "result_field_names": ["documents_total", "[redacted]"],
        }
        self.assertEqual(start_payload["execution_summary"], expected_summary)
        self.assertEqual(
            action_meta["tool"]["execution_summary"],  # type: ignore[index]
            expected_summary,
        )
        combined = json.dumps(
            {"start": start_payload, "action_meta": action_meta},
            ensure_ascii=False,
        )
        self.assertNotIn("token=hidden", combined)
        self.assertNotIn("access_token", combined)
        self.assertNotIn("api_key/secret", combined)

    def test_build_tool_runtime_semantics_meta_redacts_wrapped_execution_summary(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_search",
            kind="provider_retrieval",
            label="Provider Search",
            retryable_by_default=False,
            default_timeout_ms=21_000,
            requires_user_context=True,
            supports_result_preview=True,
            execution_kind="http_json",
            execution_summary={
                UserString("method"): UserString("POST"),
                UserString("url_origin"): UserString("https://provider.example"),
                UserString("url_path"): UserString(
                    "/v1/token=hidden/api_key/secret/search"
                ),
                UserString("response_path"): UserString("$.data.access_token"),
                UserString("result_field_names"): UserList(
                    [UserString("documents_total"), UserString("access_token")]
                ),
            },
            runner=lambda *, tool_input, prompt, user_id: {
                "documents_total": 1,
            },
            result_preview_keys=("documents_total",),
            result_output_keys=("documents_total",),
            runtime_semantic_kind="provider_search",
        )

        start_payload = build_tool_start_payload(
            task_id="task-1",
            step_id="step-1",
            name="provider_search",
            tool_input={"query": "revenue trend"},
            retry_count=0,
            registration=registration,
        )
        action_meta = build_action_step_initial_meta(
            name="provider_search",
            tool_input={"query": "revenue trend"},
            model="mock-gpt",
            label="tool_2",
            token_count=5,
            registration=registration,
        )

        expected_summary = {
            "method": "POST",
            "url_origin": "https://provider.example",
            "url_path": "/v1/[redacted]/[redacted]/[redacted]/search",
            "response_path": "$.data.[redacted]",
            "result_field_names": ["documents_total", "[redacted]"],
        }
        self.assertEqual(start_payload["execution_summary"], expected_summary)
        self.assertEqual(
            action_meta["tool"]["execution_summary"],  # type: ignore[index]
            expected_summary,
        )
        combined = json.dumps(
            {"start": start_payload, "action_meta": action_meta},
            ensure_ascii=False,
        )
        self.assertNotIn("token=hidden", combined)
        self.assertNotIn("access_token", combined)
        self.assertNotIn("api_key/secret", combined)

    def test_build_tool_runtime_semantics_meta_redacts_nested_url_execution_summary_path(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_search",
            kind="provider_retrieval",
            label="Provider Search",
            retryable_by_default=False,
            default_timeout_ms=21_000,
            requires_user_context=True,
            supports_result_preview=True,
            execution_kind="http_json",
            execution_summary={
                "method": "GET",
                "url_origin": "https://provider.example",
                "url_path": (
                    "/cb/https%3A%2F%2Fuser%3Apass%40inner.example%2Fcb/"
                    "https://api_key:secret@next.example/cb"
                ),
                "response_path": "$.data.value",
            },
            runner=lambda *, tool_input, prompt, user_id: {
                "documents_total": 1,
            },
            result_preview_keys=("documents_total",),
            result_output_keys=("documents_total",),
            runtime_semantic_kind="provider_search",
        )

        start_payload = build_tool_start_payload(
            task_id="task-1",
            step_id="step-1",
            name="provider_search",
            tool_input={"query": "revenue trend"},
            retry_count=0,
            registration=registration,
        )
        action_meta = build_action_step_initial_meta(
            name="provider_search",
            tool_input={"query": "revenue trend"},
            model="mock-gpt",
            label="tool_2",
            token_count=5,
            registration=registration,
        )

        combined = json.dumps(
            {"start": start_payload, "action_meta": action_meta},
            ensure_ascii=False,
        )
        self.assertIn("[redacted]", combined)
        self.assertNotIn("user:pass", combined)
        self.assertNotIn("user%3Apass", combined)
        self.assertNotIn("api_key:secret", combined)
        self.assertNotIn("api_key", combined)
        self.assertNotIn("secret@next", combined)

    def test_build_tool_runtime_semantics_meta_redacts_relative_query_fragment_execution_summary_path(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_search",
            kind="provider_retrieval",
            label="Provider Search",
            retryable_by_default=False,
            default_timeout_ms=21_000,
            requires_user_context=True,
            supports_result_preview=True,
            execution_kind="http_json",
            execution_summary={
                "method": "GET",
                "url_origin": "https://provider.example",
                "url_path": (
                    "/cb?access_token=secret-token&state=ok"
                    "#client_secret=hidden"
                ),
            },
            runner=lambda *, tool_input, prompt, user_id: {
                "documents_total": 1,
            },
            result_preview_keys=("documents_total",),
            result_output_keys=("documents_total",),
            runtime_semantic_kind="provider_search",
        )

        start_payload = build_tool_start_payload(
            task_id="task-1",
            step_id="step-1",
            name="provider_search",
            tool_input={"query": "revenue trend"},
            retry_count=0,
            registration=registration,
        )
        action_meta = build_action_step_initial_meta(
            name="provider_search",
            tool_input={"query": "revenue trend"},
            model="mock-gpt",
            label="tool_2",
            token_count=5,
            registration=registration,
        )

        combined = json.dumps(
            {"start": start_payload, "action_meta": action_meta},
            ensure_ascii=False,
        )
        self.assertIn("[redacted]", combined)
        self.assertNotIn("access_token", combined)
        self.assertNotIn("secret-token", combined)
        self.assertNotIn("client_secret", combined)
        self.assertNotIn("hidden", combined)

    def test_build_tool_runtime_semantics_meta_redacts_http_json_label_diagnostics(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_status",
            kind="provider_status",
            label=(
                "Provider token=hidden "
                "https://provider.example/cb?access_token=secret-token"
            ),
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
        )
        provider = StaticToolRegistryProvider(
            registry={
                "provider_status": registration,
            }
        )

        start_payload = build_tool_start_payload(
            task_id="task-1",
            step_id="step-1",
            name="provider_status",
            tool_input={"query": "demo"},
            retry_count=0,
            registration=registration,
        )
        action_meta = build_action_step_initial_meta(
            name="provider_status",
            tool_input={"query": "demo"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            registration=registration,
        )
        tool_details = build_configured_tool_registry_provider_preflight_tool_details(
            provider=provider,
        )

        combined = json.dumps(
            {
                "start": start_payload,
                "action_meta": action_meta,
                "tool_details": tool_details,
            },
            ensure_ascii=False,
        )
        self.assertIn("[redacted]", combined)
        self.assertNotIn("token=hidden", combined)
        self.assertNotIn("access_token", combined)
        self.assertNotIn("secret-token", combined)

    def test_build_tool_runtime_semantics_meta_redacts_http_json_explicit_display_name_diagnostics(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_status",
            kind="provider_status",
            label="Provider Status",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
            result_output_keys=("message",),
        )
        display_name = (
            "Provider token=hidden "
            "https://provider.example/cb?access_token=secret-token"
        )

        success_meta = build_tool_success_meta(
            name="provider_status",
            tool_input={"query": "demo"},
            output={"message": "ok"},
            retry_count=0,
            last_error=None,
            display_name=display_name,
            registration=registration,
        )
        error_meta = build_tool_error_meta(
            name="provider_status",
            tool_input={"query": "demo"},
            retry_count=0,
            error_message="failed",
            display_name=display_name,
            registration=registration,
        )
        result_summary = build_tool_result_summary(
            name="provider_status",
            output={"message": "ok"},
            display_name=display_name,
            registration=registration,
        )
        observation_entry = build_tool_observation_entry(
            name="provider_status",
            output={"message": "ok"},
            display_name=display_name,
            registration=registration,
        )

        combined = json.dumps(
            {
                "success_meta": success_meta,
                "error_meta": error_meta,
                "result_summary": result_summary,
                "observation_entry": observation_entry,
            },
            ensure_ascii=False,
        )
        self.assertIn("[redacted]", combined)
        self.assertNotIn("token=hidden", combined)
        self.assertNotIn("access_token", combined)
        self.assertNotIn("secret-token", combined)

    def test_build_tool_error_payload_and_meta_redact_http_json_raw_error_message(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_status",
            kind="provider_status",
            label="Provider Status",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
        )

        error_meta = build_tool_error_meta(
            name="provider_status",
            tool_input={"query": "demo"},
            retry_count=0,
            error_message="upstream failed token=hidden",
            registration=registration,
        )
        error_payload = build_tool_error_payload(
            name="provider_status",
            task_id="task-1",
            step_id="step-1",
            error_message="upstream failed api_key=hidden",
            retry_count=0,
            registration=registration,
        )

        self.assertEqual(
            error_meta["tool"]["error"],
            "upstream failed [redacted]",
        )
        self.assertEqual(
            error_payload["output_preview"],
            {"error": "upstream failed [redacted]"},
        )
        self.assertEqual(error_payload["error"], "upstream failed [redacted]")
        combined = json.dumps(
            {"meta": error_meta, "payload": error_payload},
            ensure_ascii=False,
        )
        self.assertNotIn("token=hidden", combined)
        self.assertNotIn("api_key=hidden", combined)
        self.assertNotIn("hidden", combined)

    def test_build_tool_error_payload_and_meta_redact_http_json_error_field_paths_and_bearer(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_status",
            kind="provider_status",
            label="Provider Status",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
        )

        error_meta = build_tool_error_meta(
            name="provider_status",
            tool_input={"query": "demo"},
            retry_count=0,
            error_message="upstream failed query_params.access_token Bearer secret-token",
            registration=registration,
        )
        error_payload = build_tool_error_payload(
            name="provider_status",
            task_id="task-1",
            step_id="step-1",
            error_message="upstream failed json_body.client_secret Bearer secret-token",
            retry_count=0,
            registration=registration,
        )

        combined = json.dumps(
            {"meta": error_meta, "payload": error_payload},
            ensure_ascii=False,
        )
        self.assertIn("[redacted]", combined)
        self.assertNotIn("access_token", combined)
        self.assertNotIn("client_secret", combined)
        self.assertNotIn("Bearer", combined)
        self.assertNotIn("secret-token", combined)

    def test_sse_error_payload_redacts_http_json_message_and_detail_diagnostics(
        self,
    ) -> None:
        payload = chat_execution_module.sse_error_payload(
            task_id="task-sse-redact",
            message=(
                "upstream failed response_path=$.data.access_token "
                "Bearer secret-token"
            ),
            code="task_stream_failure",
            fatal=True,
            retry_count=0,
            detail=(
                "callback https://provider.example/cb?access_token=secret-token"
                "#client_secret=hidden"
            ),
            status_code=502,
        )

        serialized = json.dumps(payload, ensure_ascii=False)
        self.assertIn("response_path=$.data.[redacted]", serialized)
        self.assertIn("[redacted]", serialized)
        self.assertNotIn("response_path=$.data.access_token", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertEqual(payload["task_id"], "task-sse-redact")
        self.assertEqual(payload["code"], "task_stream_failure")
        self.assertEqual(payload["status_code"], 502)

    def test_sanitize_tool_registry_artifact_payload_redacts_bare_bearer_text(
        self,
    ) -> None:
        payload = {
            "last_error": "gateway failed Bearer secret-token",
            "trace_event": {
                "step": {
                    "meta": {
                        "tool": {
                            "error": "provider failed query_params.access_token Bearer secret-token",
                        }
                    }
                }
            },
        }

        sanitized = tool_runtime_module.sanitize_tool_registry_diagnostics_artifact_payload(
            payload
        )

        serialized = json.dumps(sanitized, ensure_ascii=False)
        self.assertIn("[redacted]", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)

    def test_build_tool_phase_and_policy_keep_current_calc_defaults(self) -> None:
        ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )
        policy = build_tool_execution_policy(ctx)

        self.assertEqual(build_tool_phase(0), "tool_running")
        self.assertEqual(build_tool_phase(1), "tool_retry")
        self.assertEqual(policy["max_retry"], 1)
        self.assertEqual(policy["latency_ms"], 12)
        self.assertEqual(policy["effective_user_id"], "user-1")

    def test_build_action_step_initial_meta_and_step_keep_current_shape(self) -> None:
        meta = build_action_step_initial_meta(
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        step = build_action_step_initial_step(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            meta=meta,
        )

        self.assertEqual(meta["tool"]["name"], "calc_eval")
        self.assertEqual(meta["tool"]["label"], "Calculator")
        self.assertEqual(meta["tool"]["status"], "running")
        self.assertEqual(step["id"], "step-1")
        self.assertEqual(step["seq"], 3)
        self.assertEqual(step["content"], "Tool running: Calculator")

    def test_build_action_step_initial_meta_and_step_use_display_label_for_mock_plan(
        self,
    ) -> None:
        meta = build_action_step_initial_meta(
            name="mock_plan",
            tool_input={"prompt_preview": "请帮我规划"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        step = build_action_step_initial_step(
            step_id="step-1",
            seq=3,
            name="mock_plan",
            meta=meta,
        )

        self.assertEqual(meta["tool"]["name"], "task_plan")
        self.assertEqual(meta["tool"]["label"], "Task Planner")
        self.assertEqual(step["content"], "Tool running: Task Planner")

    def test_build_action_step_initial_meta_and_step_use_display_label_for_task_retrieve(
        self,
    ) -> None:
        meta = build_action_step_initial_meta(
            name="task_retrieve",
            tool_input={"query": "检索 demo"},
            model="mock-gpt",
            label="tool_2",
            token_count=5,
        )
        step = build_action_step_initial_step(
            step_id="step-2",
            seq=4,
            name="task_retrieve",
            meta=meta,
        )

        self.assertEqual(meta["tool"]["name"], "task_retrieve")
        self.assertEqual(meta["tool"]["label"], "Knowledge Retrieval")
        self.assertEqual(meta["tool"]["kind"], "knowledge_retrieval")
        self.assertEqual(meta["tool"]["semantic_kind"], "knowledge_retrieval")
        self.assertTrue(meta["tool"]["supports_result_preview"])
        self.assertEqual(
            meta["tool"]["effective_result_preview_keys"],
            ["hit_count", "knowledge_base_id"],
        )
        self.assertEqual(step["content"], "Tool running: Knowledge Retrieval")

    def test_build_action_step_initial_meta_includes_http_json_execution_summary(
        self,
    ) -> None:
        provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_provider_source="analytics_suite",
                tool_registry_provider_sources_json=json.dumps(
                    {
                        "analytics_suite": {
                            "provider": "default",
                            "profile": "default",
                            "disabled_tool_names": [
                                "task_plan",
                                "task_retrieve",
                                "calc_eval",
                            ],
                            "extra_tools": {
                                "provider_search": {
                                    "template": "task_retrieve",
                                    "label": "Provider Search",
                                    "kind": "provider_retrieval",
                                    "runtime_semantic_kind": "provider_search",
                                    "execution": {
                                        "kind": "http_json",
                                        "url": "https://provider.example/search",
                                        "method": "GET",
                                        "query_params": {"q": "$query", "top_k": "$top_k"},
                                        "result_fields": {
                                            "documents_total": "$.meta.total",
                                        },
                                    },
                                    "result_preview_keys": ["documents_total"],
                                    "result_output_keys": ["documents_total"],
                                }
                            },
                        }
                    }
                ),
            )
        )

        meta = build_action_step_initial_meta(
            name="provider_search",
            tool_input={"query": "检索 demo", "top_k": 3},
            model="mock-gpt",
            label="tool_2",
            token_count=5,
            registry_provider=provider,
        )

        self.assertEqual(
            meta["tool"]["execution_summary"],
            {
                "method": "GET",
                "url_origin": "https://provider.example",
                "url_path": "/search",
                "query_param_count": 2,
                "result_field_names": ["documents_total"],
            },
        )

    def test_build_action_step_initial_step_supports_registry_provider_without_explicit_label(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            registry=build_tool_registry(
                overrides={
                    "provider_search": ToolRegistration(
                        name="provider_search",
                        kind="provider_retrieval",
                        label="Hosted Search",
                        retryable_by_default=True,
                        default_timeout_ms=13_000,
                        requires_user_context=True,
                        supports_result_preview=True,
                        runner=lambda *, tool_input, prompt, user_id: {
                            "documents_total": 2,
                            "tool_kind": "provider_retrieval",
                        },
                        result_preview_keys=("documents_total",),
                        runtime_semantic_kind="provider_search",
                    )
                }
            )
        )

        step = build_action_step_initial_step(
            step_id="step-1",
            seq=3,
            name="provider_search",
            meta={"tool": {"name": "provider_search"}},
            registry_provider=provider,
        )

        self.assertEqual(step["content"], "Tool running: Hosted Search")

    def test_build_tool_attempt_start_and_success_events_keep_shape(self) -> None:
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }
        self.assertEqual(
            build_tool_attempt_start_events(
                task_id="task-1",
                step_id="step-1",
                name="calc_eval",
                tool_input={"expression": "1+2*3"},
                attempt=0,
            ),
            {
                "tool_start": {
                    "task_id": "task-1",
                    "step_id": "step-1",
                    "name": "calc_eval",
                    "display_name": "Calculator",
                    "input": {"expression": "1+2*3"},
                    "kind": "local_calculator",
                    "semantic_kind": "local_calculator",
                    "supports_result_preview": True,
                    "effective_result_preview_keys": ["expression", "result"],
                    "retry_count": 0,
                },
                "state": {
                    "task_id": "task-1",
                    "phase": "tool_running",
                },
            },
        )
        self.assertEqual(
            build_tool_attempt_success_events(
                task_id="task-1",
                step_id="step-1",
                name="calc_eval",
                output=output,
                retry_count=0,
            ),
            {
                "tool_end": {
                    "task_id": "task-1",
                    "step_id": "step-1",
                    "status": "done",
                    "latency_ms": 12,
                    "output_preview": {
                        "expression": "1+2*3",
                        "result": 7.0,
                    },
                    "kind": "local_calculator",
                    "semantic_kind": "local_calculator",
                    "supports_result_preview": True,
                    "effective_result_preview_keys": ["expression", "result"],
                    "retry_count": 0,
                }
            },
        )

    def test_build_tool_attempt_error_events_keep_shape(self) -> None:
        self.assertEqual(
            build_tool_attempt_error_events(
                name="calc_eval",
                task_id="task-1",
                step_id="step-1",
                error_message="transient",
                retry_count=1,
            ),
            {
                "tool_end": {
                    "task_id": "task-1",
                    "step_id": "step-1",
                    "status": "error",
                    "latency_ms": 12,
                    "output_preview": {"error": "transient"},
                    "kind": "local_calculator",
                    "semantic_kind": "local_calculator",
                    "supports_result_preview": True,
                    "effective_result_preview_keys": ["expression", "result"],
                    "retry_count": 1,
                    "error": "transient",
                }
            },
        )

    def test_build_tool_attempt_bundle_keeps_runtime_and_start_shapes(self) -> None:
        bundle = build_tool_attempt_bundle(
            task_id="task-1",
            step_id="step-1",
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            prompt="calc",
            user_id="user-1",
            attempt=1,
        )

        self.assertEqual(bundle["start_events"]["tool_start"]["retry_count"], 1)
        self.assertEqual(bundle["start_events"]["state"]["phase"], "tool_retry")
        self.assertEqual(bundle["runtime_ctx"].attempt, 1)
        self.assertEqual(bundle["runtime_policy"]["effective_user_id"], "user-1")

    def test_build_tool_attempt_execution_keeps_success_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        attempt_bundle = build_tool_attempt_bundle(
            task_id="task-1",
            step_id="step-1",
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        result = build_tool_attempt_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            attempt_bundle=attempt_bundle,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=output,
            exc=None,
            token_count=7,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-unused",
            rag_token_count=0,
        )

        self.assertEqual(result["start_events"]["state"]["phase"], "tool_running")
        self.assertEqual(result["tool_end_event"]["status"], "done")
        self.assertFalse(bool(result["retryable"]))
        self.assertIsNotNone(result["success_effects"])
        self.assertIsNone(result["terminal_effects"])

    def test_build_tool_attempt_execution_keeps_terminal_failure_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        attempt_bundle = build_tool_attempt_bundle(
            task_id="task-1",
            step_id="step-1",
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            prompt="calc",
            user_id="user-1",
            attempt=1,
        )

        result = build_tool_attempt_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            attempt_bundle=attempt_bundle,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=None,
            exc=MockToolExecutionError("transient", fatal=False),
            token_count=9,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-unused",
            rag_token_count=0,
        )

        self.assertEqual(result["start_events"]["state"]["phase"], "tool_retry")
        self.assertEqual(result["tool_end_event"]["status"], "error")
        self.assertFalse(bool(result["retryable"]))
        self.assertIsNone(result["success_effects"])
        self.assertIsNotNone(result["terminal_effects"])

    def test_build_tool_attempt_loop_result_keeps_success_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        attempt_bundle = build_tool_attempt_bundle(
            task_id="task-1",
            step_id="step-1",
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }
        attempt_execution = build_tool_attempt_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            attempt_bundle=attempt_bundle,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=output,
            exc=None,
            token_count=7,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-unused",
            rag_token_count=0,
        )

        loop_result = build_tool_attempt_loop_result(
            attempt_execution=attempt_execution,
        )

        self.assertEqual(loop_result["tool_end_event"]["status"], "done")
        self.assertFalse(bool(loop_result["retryable"]))
        self.assertIsNotNone(loop_result["success_effects"])
        self.assertIsNone(loop_result["terminal_effects"])

    def test_build_tool_attempt_loop_result_keeps_terminal_failure_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        attempt_bundle = build_tool_attempt_bundle(
            task_id="task-1",
            step_id="step-1",
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            prompt="calc",
            user_id="user-1",
            attempt=1,
        )
        attempt_execution = build_tool_attempt_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            attempt_bundle=attempt_bundle,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=None,
            exc=MockToolExecutionError("transient", fatal=False),
            token_count=9,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-unused",
            rag_token_count=0,
        )

        loop_result = build_tool_attempt_loop_result(
            attempt_execution=attempt_execution,
        )

        self.assertEqual(loop_result["tool_end_event"]["status"], "error")
        self.assertFalse(bool(loop_result["retryable"]))
        self.assertIsNone(loop_result["success_effects"])
        self.assertIsNotNone(loop_result["terminal_effects"])

    def test_build_tool_attempt_loop_result_redacts_terminal_diagnostics_payload(
        self,
    ) -> None:
        attempt_execution = {
            "tool_end_event": {
                "status": "error",
                "message": "provider_search failed with token=hidden",
            },
            "error_event": {
                "code": "tool_execution_error",
                "message": (
                    "provider_search: http_json execution query_params.access_token must be safe"
                ),
            },
            "retryable": False,
            "next_action_step": {
                "id": "step-1",
                "seq": 3,
                "content": (
                    "provider_search: unsupported tool execution kind api_key=hidden"
                ),
            },
            "last_error": "provider_search failed with token=hidden",
            "plan_item_result": {
                "outcome": "terminal_failure",
                "error": "headers.x-api-key is invalid",
            },
            "postprocess": None,
            "success_effects": None,
            "terminal_effects": {
                "trace_step": {
                    "id": "step-1",
                    "seq": 3,
                    "content": (
                        "provider_search: unsupported tool execution kind api_key=hidden"
                    ),
                },
                "trace": {
                    "task_id": "task-1",
                    "step_id": "step-1",
                    "step": {
                        "id": "step-1",
                        "seq": 3,
                        "content": (
                            "provider_search: http_json execution json_body.client_secret must be safe"
                        ),
                    },
                },
                "status": "failed",
                "error_message": "provider_search failed with token=hidden",
                "audit_detail": {
                    "path": "query_params.access_token",
                    "message": "api_key=hidden",
                },
                "state": {
                    "task_id": "task-1",
                    "phase": "error",
                    "message": "token=hidden",
                },
            },
        }

        loop_result = build_tool_attempt_loop_result(
            attempt_execution=attempt_execution,
        )

        serialized = json.dumps(loop_result, default=str)
        self.assertNotIn("api_key=hidden", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("x-api-key", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertIn("unsupported tool execution kind [redacted]", serialized)
        self.assertIn("http_json execution [redacted] must be safe", serialized)

    def test_build_tool_attempt_loop_result_redacts_http_json_trace_step_outputs(
        self,
    ) -> None:
        raw_step = self._make_sensitive_http_json_action_step(
            step_id="step-attempt-loop-http-json-output"
        )
        attempt_execution = {
            "tool_end_event": {"status": "done"},
            "error_event": None,
            "retryable": False,
            "next_action_step": raw_step,
            "last_error": None,
            "plan_item_result": {"outcome": "success"},
            "postprocess": None,
            "success_effects": {
                "trace_step": raw_step,
                "trace": {
                    "task_id": "task-1",
                    "step_id": "step-attempt-loop-http-json-output",
                    "step": raw_step,
                },
                "observation": "Provider Status: ok",
                "output": {"status": "ready"},
                "rag_followup": None,
            },
            "terminal_effects": None,
        }

        result = build_tool_attempt_loop_result(
            attempt_execution=attempt_execution,
        )

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertIn("gateway [redacted]", serialized)
        self.assertIn("preview [redacted]", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn('"request_id"', serialized)

    def test_build_tool_attempt_loop_result_redacts_http_json_rag_followup_trace_outputs(
        self,
    ) -> None:
        raw_step = self._make_sensitive_http_json_action_step(
            step_id="step-attempt-loop-http-json-rag-followup-output"
        )
        rag_followup_step = self._make_sensitive_http_json_action_step(
            step_id="rag-attempt-loop-http-json-output",
            content="Retrieved snippets",
        )
        attempt_execution = {
            "tool_end_event": {"status": "done"},
            "error_event": None,
            "retryable": False,
            "next_action_step": raw_step,
            "last_error": None,
            "plan_item_result": {"outcome": "success"},
            "postprocess": None,
            "success_effects": {
                "trace_step": raw_step,
                "trace": {
                    "task_id": "task-1",
                    "step_id": "step-attempt-loop-http-json-rag-followup-output",
                    "step": raw_step,
                },
                "observation": "Provider Status: ok",
                "output": {"status": "ready"},
                "rag_followup": {
                    "step": rag_followup_step,
                    "trace": {
                        "task_id": "task-1",
                        "step_id": "rag-attempt-loop-http-json-output",
                        "step": rag_followup_step,
                    },
                },
            },
            "terminal_effects": None,
        }

        result = build_tool_attempt_loop_result(
            attempt_execution=attempt_execution,
        )

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertIn("gateway [redacted]", serialized)
        self.assertIn("preview [redacted]", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn('"request_id"', serialized)

    def test_build_tool_attempt_loop_result_redacts_http_json_postprocess_rag_followup_trace_outputs(
        self,
    ) -> None:
        raw_step = self._make_sensitive_http_json_action_step(
            step_id="step-attempt-loop-http-json-postprocess-output"
        )
        rag_followup_step = self._make_sensitive_http_json_action_step(
            step_id="rag-attempt-loop-http-json-postprocess-output",
            content="Retrieved snippets",
        )
        attempt_execution = {
            "tool_end_event": {"status": "done"},
            "error_event": None,
            "retryable": False,
            "next_action_step": raw_step,
            "last_error": None,
            "plan_item_result": {"outcome": "success"},
            "postprocess": {
                "trace": {
                    "task_id": "task-1",
                    "step_id": "step-attempt-loop-http-json-postprocess-output",
                    "step": raw_step,
                },
                "observation": "Provider Status: ok",
                "output": {"status": "ready"},
                "rag_followup": {
                    "step": rag_followup_step,
                    "trace": {
                        "task_id": "task-1",
                        "step_id": "rag-attempt-loop-http-json-postprocess-output",
                        "step": rag_followup_step,
                    },
                },
            },
            "success_effects": {
                "trace_step": raw_step,
                "trace": {
                    "task_id": "task-1",
                    "step_id": "step-attempt-loop-http-json-postprocess-output",
                    "step": raw_step,
                },
                "observation": "Provider Status: ok",
                "output": {"status": "ready"},
                "rag_followup": None,
            },
            "terminal_effects": None,
        }

        result = build_tool_attempt_loop_result(
            attempt_execution=attempt_execution,
        )

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertIn("gateway [redacted]", serialized)
        self.assertIn("preview [redacted]", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn('"request_id"', serialized)

    def test_build_tool_attempt_loop_terminal_result_keeps_success_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        attempt_bundle = build_tool_attempt_bundle(
            task_id="task-1",
            step_id="step-1",
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }
        attempt_execution = build_tool_attempt_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            attempt_bundle=attempt_bundle,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=output,
            exc=None,
            token_count=7,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-unused",
            rag_token_count=0,
        )
        loop_result = build_tool_attempt_loop_result(
            attempt_execution=attempt_execution,
        )

        terminal = build_tool_attempt_loop_terminal_result(
            loop_result=loop_result,
        )

        self.assertFalse(bool(terminal["should_return"]))
        self.assertIsNone(terminal["terminal_effects"])

    def test_build_tool_attempt_loop_terminal_result_keeps_terminal_failure_shape(self) -> None:
        iteration_ctx = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )
        attempt_bundle = build_tool_attempt_bundle(
            task_id="task-1",
            step_id="step-1",
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            prompt="calc",
            user_id="user-1",
            attempt=1,
        )
        attempt_execution = build_tool_attempt_execution(
            task_id="task-1",
            iteration_ctx=iteration_ctx,
            action_step=iteration_ctx["action_step"],
            attempt_bundle=attempt_bundle,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=None,
            exc=MockToolExecutionError("transient", fatal=False),
            token_count=9,
            last_error=None,
            model="mock-gpt",
            rag_step_id="rag-unused",
            rag_token_count=0,
        )
        loop_result = build_tool_attempt_loop_result(
            attempt_execution=attempt_execution,
        )

        terminal = build_tool_attempt_loop_terminal_result(
            loop_result=loop_result,
        )

        self.assertTrue(bool(terminal["should_return"]))
        self.assertIsNotNone(terminal["terminal_effects"])
        self.assertEqual(terminal["terminal_effects"]["state"]["phase"], "error")

    def test_build_tool_attempt_loop_terminal_result_redacts_diagnostics_payload(
        self,
    ) -> None:
        loop_result = {
            "terminal_effects": {
                "trace_step": {
                    "id": "step-1",
                    "seq": 3,
                    "content": (
                        "provider_search: unsupported tool execution kind api_key=hidden"
                    ),
                },
                "trace": {
                    "task_id": "task-1",
                    "step_id": "step-1",
                    "step": {
                        "id": "step-1",
                        "seq": 3,
                        "content": (
                            "provider_search: http_json execution headers.x-api-key must be safe"
                        ),
                    },
                },
                "status": "failed",
                "error_message": "provider_search failed with token=hidden",
                "audit_detail": {
                    "path": "json_body.client_secret",
                    "message": "api_key=hidden",
                },
                "state": {
                    "task_id": "task-1",
                    "phase": "error",
                    "message": "token=hidden",
                },
            },
        }

        result = build_tool_attempt_loop_terminal_result(
            loop_result=loop_result,
        )

        serialized = json.dumps(result, default=str)
        self.assertNotIn("api_key=hidden", serialized)
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("x-api-key", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertIn("unsupported tool execution kind [redacted]", serialized)
        self.assertIn("http_json execution [redacted] must be safe", serialized)

    def test_build_tool_plan_item_retry_loop_result_keeps_success_shape(self) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool done: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "done",
                    "output": {
                        "expression": "1+2*3",
                        "result": 7.0,
                        "tool_kind": "local_calculator",
                    },
                }
            },
        }
        success_effects = {
            "trace_step": action_step,
            "trace": {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": action_step,
            },
            "observation": 'calc_eval: {"expression": "1+2*3", "result": 7.0, "tool_kind": "local_calculator"}',
            "output": {
                "expression": "1+2*3",
                "result": 7.0,
                "tool_kind": "local_calculator",
            },
            "rag_followup": None,
        }
        loop_result = {
            "tool_end_event": {"status": "done"},
            "error_event": None,
            "retryable": False,
            "next_action_step": action_step,
            "last_error": None,
            "plan_item_result": {"outcome": "success"},
            "postprocess": {"trace": success_effects["trace"]},
            "success_effects": success_effects,
            "terminal_effects": None,
        }

        result = build_tool_plan_item_retry_loop_result(
            loop_result=loop_result,
        )

        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["trace_event"]["step"]["content"], "Tool done: calc_eval")
        self.assertIsNotNone(result["success_effects"])
        self.assertIsNone(result["terminal_effects"])

    def test_build_tool_plan_item_retry_loop_result_keeps_terminal_failure_shape(self) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool error: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "error",
                }
            },
        }
        terminal_effects = {
            "trace_step": action_step,
            "trace": {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": action_step,
            },
            "status": "failed",
            "error_message": "transient",
            "audit_detail": {"step_id": "step-1", "retry_count": 2},
            "state": {"task_id": "task-1", "phase": "error"},
        }
        loop_result = {
            "tool_end_event": {"status": "error"},
            "error_event": {"code": "tool_execution_error"},
            "retryable": False,
            "next_action_step": action_step,
            "last_error": "transient",
            "plan_item_result": {"outcome": "terminal_failure"},
            "postprocess": None,
            "success_effects": None,
            "terminal_effects": terminal_effects,
        }

        result = build_tool_plan_item_retry_loop_result(
            loop_result=loop_result,
        )

        self.assertEqual(result["outcome"], "terminal_failure")
        self.assertEqual(result["trace_event"]["step"]["content"], "Tool error: calc_eval")
        self.assertIsNone(result["success_effects"])
        self.assertIsNotNone(result["terminal_effects"])

    def test_build_tool_plan_item_retry_loop_result_redacts_terminal_diagnostics_payload(
        self,
    ) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": (
                "provider_search: unsupported tool execution kind api_key=hidden"
            ),
        }
        terminal_effects = {
            "trace_step": action_step,
            "trace": {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": {
                    **action_step,
                    "content": (
                        "provider_search: http_json execution query_params.access_token must be safe"
                    ),
                },
            },
            "status": "failed",
            "error_message": "provider_search failed with token=hidden",
            "audit_detail": {
                "path": "headers.x-api-key",
                "message": "json_body.client_secret is invalid",
            },
            "state": {
                "task_id": "task-1",
                "phase": "error",
                "message": "api_key=hidden",
            },
        }
        loop_result = {
            "tool_end_event": {"status": "error"},
            "error_event": {"code": "tool_execution_error"},
            "retryable": False,
            "next_action_step": action_step,
            "last_error": "provider_search failed with token=hidden",
            "plan_item_result": {"outcome": "terminal_failure"},
            "postprocess": None,
            "success_effects": None,
            "terminal_effects": terminal_effects,
        }

        result = build_tool_plan_item_retry_loop_result(
            loop_result=loop_result,
        )

        serialized = json.dumps(result, default=str)
        self.assertNotIn("api_key=hidden", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("x-api-key", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertIn("unsupported tool execution kind [redacted]", serialized)
        self.assertIn("http_json execution [redacted] must be safe", serialized)

    def test_build_tool_plan_item_retry_loop_result_redacts_http_json_trace_step_outputs(
        self,
    ) -> None:
        raw_step = self._make_sensitive_http_json_action_step(
            step_id="step-retry-loop-http-json-output"
        )
        success_effects = {
            "trace_step": raw_step,
            "trace": {
                "task_id": "task-1",
                "step_id": "step-retry-loop-http-json-output",
                "step": raw_step,
            },
            "observation": "Provider Status: ok",
            "output": {"status": "ready"},
            "rag_followup": None,
        }
        loop_result = {
            "tool_end_event": {"status": "done"},
            "error_event": None,
            "retryable": False,
            "next_action_step": raw_step,
            "last_error": None,
            "plan_item_result": {"outcome": "success"},
            "postprocess": {"trace": success_effects["trace"]},
            "success_effects": success_effects,
            "terminal_effects": None,
        }

        result = build_tool_plan_item_retry_loop_result(
            loop_result=loop_result,
        )

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertIn("gateway [redacted]", serialized)
        self.assertIn("preview [redacted]", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn('"request_id"', serialized)

    def test_build_tool_plan_item_retry_loop_execution_result_redacts_loop_diagnostics_payload(
        self,
    ) -> None:
        action_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": (
                "provider_search: unsupported tool execution kind api_key=hidden"
            ),
        }
        terminal_effects = {
            "trace_step": action_step,
            "trace": {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": {
                    **action_step,
                    "content": (
                        "provider_search: http_json execution json_body.client_secret must be safe"
                    ),
                },
            },
            "status": "failed",
            "error_message": "provider_search failed with token=hidden",
            "audit_detail": {
                "path": "query_params.access_token",
                "message": "headers.x-api-key is invalid",
            },
            "state": {
                "task_id": "task-1",
                "phase": "error",
                "message": "api_key=hidden",
            },
        }
        loop_result = {
            "tool_end_event": {
                "status": "error",
                "message": "provider_search failed with token=hidden",
            },
            "error_event": {
                "code": "tool_execution_error",
                "message": "headers.x-api-key is invalid",
            },
            "retryable": False,
            "next_action_step": action_step,
            "last_error": "provider_search failed with token=hidden",
            "plan_item_result": {
                "outcome": "terminal_failure",
                "error": "json_body.client_secret is invalid",
            },
            "postprocess": None,
            "success_effects": None,
            "terminal_effects": terminal_effects,
        }

        result = build_tool_plan_item_retry_loop_execution_result(
            loop_result=loop_result,
        )

        serialized = json.dumps(result, default=str)
        self.assertNotIn("api_key=hidden", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("x-api-key", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertIn("unsupported tool execution kind [redacted]", serialized)
        self.assertIn("http_json execution [redacted] must be safe", serialized)

    def test_build_tool_plan_item_retry_loop_execution_result_redacts_http_json_trace_step_outputs(
        self,
    ) -> None:
        raw_step = self._make_sensitive_http_json_action_step(
            step_id="step-retry-loop-execution-http-json-output"
        )
        success_effects = {
            "trace_step": raw_step,
            "trace": {
                "task_id": "task-1",
                "step_id": "step-retry-loop-execution-http-json-output",
                "step": raw_step,
            },
            "observation": "Provider Status: ok",
            "output": {"status": "ready"},
            "rag_followup": None,
        }
        loop_result = {
            "tool_end_event": {"status": "done"},
            "error_event": None,
            "retryable": False,
            "next_action_step": raw_step,
            "last_error": None,
            "plan_item_result": {"outcome": "success"},
            "postprocess": {"trace": success_effects["trace"]},
            "success_effects": success_effects,
            "terminal_effects": None,
        }

        result = build_tool_plan_item_retry_loop_execution_result(
            loop_result=loop_result,
        )

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertIn("gateway [redacted]", serialized)
        self.assertIn("preview [redacted]", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertNotIn('"request_id"', serialized)

    def test_build_tool_step_updates_keep_current_shape(self) -> None:
        base_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool running: calc_eval",
            "meta": {
                "model": "mock-gpt",
                "step_type": "tool_call",
                "label": "tool_1",
                "retryCount": 0,
                "tokens": 5,
                "cost_estimate": None,
                "tool": {
                    "name": "calc_eval",
                    "input": {"expression": "1+2*3"},
                    "status": "running",
                    "retry_count": 0,
                },
            },
        }
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        success_step = build_tool_step_success_update(
            action_step=base_step,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=output,
            retry_count=0,
            token_count=7,
            last_error=None,
        )
        error_step = build_tool_step_error_update(
            action_step=base_step,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            retry_count=1,
            token_count=9,
            error_message="transient",
        )

        self.assertEqual(success_step["content"], "Tool done: Calculator")
        self.assertEqual(success_step["meta"]["tool"]["status"], "done")
        self.assertEqual(error_step["content"], "Tool error: Calculator")
        self.assertEqual(error_step["meta"]["tool"]["status"], "error")

    def test_build_tool_step_error_update_redacts_legacy_error_payload(self) -> None:
        registration = ToolRegistration(
            name="provider_search",
            kind="provider_retrieval",
            label="Provider Search",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            runner=lambda *, tool_input, prompt, user_id: {},
            execution_kind="http_json",
        )
        base_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool running: Provider Search",
            "meta": {
                "model": "mock-gpt",
                "step_type": "tool_call",
                "legacy_error": (
                    "provider_search: http_json execution query_params.access_token must be safe"
                ),
                "tool": {
                    "name": "provider_search",
                    "status": "running",
                    "legacy_error": (
                        "provider_search: unsupported tool execution kind api_key=hidden"
                    ),
                },
            },
        }

        error_step = build_tool_step_error_update(
            action_step=base_step,
            name="provider_search",
            tool_input={"query": "demo"},
            retry_count=1,
            token_count=9,
            error_message="provider_search failed with token=hidden",
            registration=registration,
        )

        serialized = json.dumps(error_step, default=str)
        self.assertNotIn("api_key=hidden", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertIn("http_json execution [redacted] must be safe", serialized)
        self.assertIn("provider_search failed with [redacted]", serialized)

    def test_build_tool_step_updates_support_registry_provider_without_explicit_label_or_registration(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            registry=build_tool_registry(
                overrides={
                    "provider_search": ToolRegistration(
                        name="provider_search",
                        kind="provider_retrieval",
                        label="Hosted Search",
                        retryable_by_default=True,
                        default_timeout_ms=13_000,
                        requires_user_context=True,
                        supports_result_preview=True,
                        runner=lambda *, tool_input, prompt, user_id: {
                            "documents_total": 2,
                            "tool_kind": "provider_retrieval",
                        },
                        result_preview_keys=("documents_total",),
                        runtime_semantic_kind="provider_search",
                    )
                }
            )
        )
        base_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool running: provider_search",
            "meta": {
                "model": "mock-gpt",
                "step_type": "tool_call",
                "label": "tool_1",
                "retryCount": 0,
                "tokens": 5,
                "cost_estimate": None,
                "tool": {
                    "name": "provider_search",
                    "input": {"query": "revenue trend"},
                    "status": "running",
                    "retry_count": 0,
                },
            },
        }

        success_step = build_tool_step_success_update(
            action_step=base_step,
            name="provider_search",
            tool_input={"query": "revenue trend"},
            output={
                "documents_total": 2,
                "tool_kind": "provider_retrieval",
            },
            retry_count=0,
            token_count=7,
            last_error=None,
            registry_provider=provider,
        )
        error_step = build_tool_step_error_update(
            action_step=base_step,
            name="provider_search",
            tool_input={"query": "revenue trend"},
            retry_count=1,
            token_count=9,
            error_message="transient",
            registry_provider=provider,
        )

        self.assertEqual(success_step["content"], "Tool done: Hosted Search")
        self.assertEqual(error_step["content"], "Tool error: Hosted Search")

    def test_build_tool_attempt_success_transition_keeps_current_shape(self) -> None:
        base_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool running: calc_eval",
            "meta": {
                "model": "mock-gpt",
                "step_type": "tool_call",
                "label": "tool_1",
                "retryCount": 0,
                "tokens": 5,
                "cost_estimate": None,
                "tool": {
                    "name": "calc_eval",
                    "input": {"expression": "1+2*3"},
                    "status": "running",
                    "retry_count": 0,
                },
            },
        }
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        transition = build_tool_attempt_success_transition(
            task_id="task-1",
            step_id="step-1",
            action_step=base_step,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=output,
            retry_count=0,
            token_count=7,
            last_error=None,
        )

        self.assertEqual(transition["action_step"]["content"], "Tool done: Calculator")
        self.assertEqual(transition["action_step"]["meta"]["tool"]["status"], "done")
        self.assertEqual(
            transition["events"]["tool_end"],
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "status": "done",
                "latency_ms": 12,
                "output_preview": {
                    "expression": "1+2*3",
                    "result": 7.0,
                },
                "kind": "local_calculator",
                "semantic_kind": "local_calculator",
                "supports_result_preview": True,
                "effective_result_preview_keys": ["expression", "result"],
                "retry_count": 0,
            },
        )

    def test_build_tool_attempt_error_transition_keeps_current_shape(self) -> None:
        base_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool running: calc_eval",
            "meta": {
                "model": "mock-gpt",
                "step_type": "tool_call",
                "label": "tool_1",
                "retryCount": 0,
                "tokens": 5,
                "cost_estimate": None,
                "tool": {
                    "name": "calc_eval",
                    "input": {"expression": "1+2*3"},
                    "status": "running",
                    "retry_count": 0,
                },
            },
        }
        ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )
        exc = MockToolExecutionError("transient", fatal=False)

        transition = build_tool_attempt_error_transition(
            task_id="task-1",
            step_id="step-1",
            action_step=base_step,
            runtime_ctx=ctx,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            exc=exc,
            token_count=9,
        )

        self.assertEqual(transition["action_step"]["content"], "Tool error: Calculator")
        self.assertEqual(transition["action_step"]["meta"]["tool"]["status"], "error")
        self.assertTrue(transition["retryable"])
        self.assertEqual(
            transition["events"]["tool_end"],
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "status": "error",
                "latency_ms": 12,
                "output_preview": {"error": "transient"},
                "kind": "local_calculator",
                "semantic_kind": "local_calculator",
                "supports_result_preview": True,
                "effective_result_preview_keys": ["expression", "result"],
                "retry_count": 1,
                "error": "transient",
            },
        )
        self.assertEqual(
            transition["events"]["error"],
            {
                "task_id": "task-1",
                "message": "transient",
                "code": "tool_execution_error",
                "fatal": False,
                "retryable": True,
                "retryCount": 1,
                "step_id": "step-1",
            },
        )

    def test_build_tool_attempt_error_transition_redacts_http_json_error_event_message(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_status",
            kind="provider_status",
            label="Provider Status",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            execution_kind="http_json",
            runner=lambda *, tool_input, prompt, user_id: {},
        )
        base_step = build_action_step_initial_step(
            step_id="step-1",
            seq=3,
            name="provider_status",
            meta=build_action_step_initial_meta(
                name="provider_status",
                tool_input={"query": "status"},
                model="mock-gpt",
                label="tool_1",
                token_count=5,
                registration=registration,
            ),
            registration=registration,
        )
        ctx = build_tool_runtime_context(
            name="provider_status",
            prompt="status",
            user_id="user-1",
            attempt=0,
            registry={"provider_status": registration},
        )
        exc = MockToolExecutionError(
            "upstream failed token=hidden api_key=hidden",
            fatal=True,
        )

        transition = build_tool_attempt_error_transition(
            task_id="task-1",
            step_id="step-1",
            action_step=base_step,
            runtime_ctx=ctx,
            name="provider_status",
            tool_input={"query": "status"},
            exc=exc,
            token_count=9,
            registry={"provider_status": registration},
        )
        terminal = build_tool_terminal_failure_transition(
            task_id="task-1",
            step_id="step-1",
            action_step=transition["action_step"],  # type: ignore[arg-type]
            error_message=str(transition["error_message"]),
            retry_count=int(transition["retry_count"]),
        )

        self.assertEqual(
            transition["events"]["tool_end"]["output_preview"],
            {"error": "upstream failed [redacted] [redacted]"},
        )
        self.assertEqual(
            transition["events"]["error"]["message"],  # type: ignore[index]
            "upstream failed [redacted] [redacted]",
        )
        self.assertEqual(
            transition["error_message"],
            "upstream failed [redacted] [redacted]",
        )
        self.assertEqual(
            terminal["error_message"],
            "upstream failed [redacted] [redacted]",
        )
        combined = json.dumps(
            {"transition": transition, "terminal": terminal},
            ensure_ascii=False,
        )
        self.assertNotIn("token=hidden", combined)
        self.assertNotIn("api_key=hidden", combined)
        self.assertNotIn("hidden", combined)

    def test_build_tool_attempt_error_transition_honors_runtime_timeout(self) -> None:
        base_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool running: Custom Lookup",
            "meta": {
                "model": "mock-gpt",
                "step_type": "tool_call",
                "label": "tool_1",
                "retryCount": 0,
                "tokens": 5,
                "cost_estimate": None,
                "tool": {
                    "name": "custom_lookup",
                    "label": "Custom Lookup",
                    "input": {"query": "secret"},
                    "status": "running",
                    "retry_count": 0,
                },
            },
        }
        registry = {
            "custom_lookup": ToolRegistration(
                name="custom_lookup",
                kind="custom_lookup",
                label="Custom Lookup",
                retryable_by_default=False,
                default_timeout_ms=12_000,
                requires_user_context=False,
                supports_result_preview=False,
                runner=lambda *, tool_input, prompt, user_id: {
                    "tool_input": tool_input,
                },
            )
        }
        ctx = build_tool_runtime_context(
            name="custom_lookup",
            prompt="lookup",
            user_id="user-1",
            attempt=0,
            registry=registry,
        )
        exc = MockToolExecutionError("fatal", fatal=True)

        transition = build_tool_attempt_error_transition(
            task_id="task-1",
            step_id="step-1",
            action_step=base_step,
            runtime_ctx=ctx,
            name="custom_lookup",
            tool_input={"query": "secret"},
            exc=exc,
            token_count=9,
            display_name="Custom Lookup",
        )

        self.assertEqual(transition["events"]["tool_end"]["latency_ms"], 48)
        self.assertEqual(
            transition["events"]["tool_end"]["output_preview"],
            {"error": "fatal"},
        )

    def test_build_tool_step_output_returns_output_dict_when_present(self) -> None:
        step = {
            "meta": {
                "tool": {
                    "output": {
                        "result": 7.0,
                    }
                }
            }
        }

        self.assertEqual(build_tool_step_output(step), {"result": 7.0})

    def test_build_tool_step_output_redacts_http_json_raw_output_dict(self) -> None:
        step = {
            "meta": {
                "tool": {
                    "name": "provider_status",
                    "label": "Provider Status",
                    "execution_kind": "http_json",
                    "effective_result_output_keys": ["status", "message"],
                    "output": {
                        "status": "ready",
                        "message": "gateway token=hidden",
                        "access_token": "secret-token",
                        "request_id": "Bearer secret-token",
                    },
                }
            }
        }

        output = build_tool_step_output(step)

        self.assertEqual(
            output,
            {
                "status": "ready",
                "message": "gateway token=[redacted]",
            },
        )
        serialized = json.dumps(output, ensure_ascii=False)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)

    def test_build_tool_step_output_redacts_http_json_raw_preview_dict(self) -> None:
        step = {
            "meta": {
                "tool": {
                    "name": "provider_status",
                    "label": "Provider Status",
                    "execution_kind": "http_json",
                    "output_preview": {
                        "status": "ready",
                        "message": "gateway token=hidden",
                        "access_token": "secret-token",
                        "request_id": "Bearer secret-token",
                    },
                }
            }
        }

        output = build_tool_step_output(step)

        self.assertEqual(
            output,
            {
                "status": "ready",
                "message": "gateway token=[redacted]",
                "access_token": "[redacted]",
            },
        )
        serialized = json.dumps(output, ensure_ascii=False)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)

    def test_build_tool_step_success_update_keeps_raw_output_and_stores_preview(
        self,
    ) -> None:
        base_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool running: Custom Lookup",
            "meta": {
                "model": "mock-gpt",
                "step_type": "tool_call",
                "label": "tool_1",
                "retryCount": 0,
                "tokens": 5,
                "cost_estimate": None,
                "tool": {
                    "name": "custom_lookup",
                    "label": "Custom Lookup",
                    "input": {"query": "secret"},
                    "status": "running",
                    "retry_count": 0,
                },
            },
        }
        registration = ToolRegistration(
            name="custom_lookup",
            kind="custom_lookup",
            label="Custom Lookup",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            result_preview_keys=("tool_kind", "hit_count"),
            runner=lambda *, tool_input, prompt, user_id: {
                "tool_input": tool_input,
                "prompt": prompt,
                "user_id": user_id,
            },
        )
        output = {
            "tool_kind": "custom_lookup",
            "hit_count": 1,
            "secret": "do-not-preview",
        }

        success_step = build_tool_step_success_update(
            action_step=base_step,
            name="custom_lookup",
            tool_input={"query": "secret"},
            output=output,
            retry_count=0,
            token_count=7,
            last_error=None,
            display_name="Custom Lookup",
            registration=registration,
        )

        self.assertEqual(success_step["meta"]["tool"]["output"], output)
        self.assertEqual(
            success_step["meta"]["tool"]["output_preview"],
            {
                "tool_kind": "custom_lookup",
                "hit_count": 1,
            },
        )

    def test_build_tool_observation_entry_prefers_preview_shape_for_builtin_calculator(self) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="calc_eval",
                output={
                    "expression": "1+2*3",
                    "result": 7.0,
                    "tool_kind": "local_calculator",
                },
            ),
            'Calculator: {"expression": "1+2*3", "result": 7.0}',
        )

    def test_build_tool_observation_entry_prefers_result_summary_for_runtime_override_real_tool(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_search",
            kind="provider_retrieval",
            label="Provider Search",
            retryable_by_default=False,
            default_timeout_ms=13_000,
            requires_user_context=True,
            supports_result_preview=True,
            result_preview_keys=("documents_total",),
            result_output_keys=("documents_total", "request_id"),
            runtime_semantic_kind="provider_search",
            runner=lambda *, tool_input, prompt, user_id: {
                "tool_input": tool_input,
                "prompt": prompt,
                "user_id": user_id,
            },
        )

        self.assertEqual(
            build_tool_observation_entry(
                name="provider_search",
                output={
                    "documents_total": 2,
                    "request_id": "req-1",
                    "documents": [{"id": "doc-1"}],
                    "tool_kind": "provider_retrieval",
                },
                registration=registration,
            ),
            "Provider Search: Retrieved 2 documents (request id req-1).",
        )

    def test_build_tool_observation_entry_reuses_step_meta_preview_without_registry_context(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="custom_lookup",
                output={
                    "tool_kind": "custom_lookup",
                    "hit_count": 1,
                    "secret": "do-not-preview",
                },
                step_tool_meta={
                    "name": "custom_lookup",
                    "label": "Custom Lookup",
                    "status": "done",
                    "output": {
                        "tool_kind": "custom_lookup",
                        "hit_count": 1,
                        "secret": "do-not-preview",
                    },
                    "output_preview": {
                        "tool_kind": "custom_lookup",
                        "hit_count": 1,
                    },
                },
            ),
            'Custom Lookup: {"tool_kind": "custom_lookup", "hit_count": 1}',
        )

    def test_build_tool_observation_entry_reuses_step_meta_result_summary_without_output(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="provider_search",
                output=None,
                step_tool_meta={
                    "name": "provider_search",
                    "label": "Provider Search",
                    "status": "done",
                    "result_summary": "Retrieved 2 documents (request id req-1).",
                    "output_preview": {
                        "documents_total": 2,
                    },
                },
            ),
            "Provider Search: Retrieved 2 documents (request id req-1).",
        )

    def test_build_tool_observation_entry_redacts_http_json_step_meta_result_summary(
        self,
    ) -> None:
        observation = build_tool_observation_entry(
            name="provider_status",
            output=None,
            step_tool_meta={
                "name": "provider_status",
                "label": "Provider Status",
                "status": "done",
                "execution_kind": "http_json",
                "result_summary": (
                    "Provider Status output - status=ready, "
                    "message=query_params.access_token Bearer secret-token."
                ),
            },
        )

        self.assertEqual(
            observation,
            "Provider Status: Provider Status output - status=ready, "
            "message=[redacted] [redacted]",
        )
        self.assertNotIn("access_token", observation)
        self.assertNotIn("Bearer", observation)
        self.assertNotIn("secret-token", observation)

    def test_build_tool_observation_entry_infers_result_summary_from_step_meta_safe_output_without_output(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_search",
            kind="provider_retrieval",
            label="Provider Search",
            retryable_by_default=False,
            default_timeout_ms=13_000,
            requires_user_context=True,
            supports_result_preview=True,
            result_preview_keys=("documents_total",),
            result_output_keys=("documents_total", "request_id"),
            runtime_semantic_kind="provider_search",
            runner=lambda *, tool_input, prompt, user_id: {
                "tool_input": tool_input,
                "prompt": prompt,
                "user_id": user_id,
            },
        )

        self.assertEqual(
            build_tool_observation_entry(
                name="provider_search",
                output=None,
                registration=registration,
                step_tool_meta={
                    "name": "provider_search",
                    "label": "Provider Search",
                    "status": "done",
                    "effective_result_output_keys": [
                        "documents_total",
                        "request_id",
                    ],
                    "output": {
                        "documents_total": 2,
                        "request_id": "req-1",
                        "documents": [{"id": "doc-1"}],
                    },
                    "output_preview": {
                        "documents_total": 2,
                    },
                },
            ),
            "Provider Search: Retrieved 2 documents (request id req-1).",
        )

    def test_build_tool_observation_entry_infers_result_summary_from_step_meta_preview_without_output(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="task_plan",
            kind="planner",
            label="Task Planner",
            retryable_by_default=False,
            default_timeout_ms=13_000,
            requires_user_context=True,
            supports_result_preview=True,
            result_preview_keys=("plan",),
            result_output_keys=("plan",),
            runtime_semantic_kind="task_planner",
            runner=lambda *, tool_input, prompt, user_id: {
                "tool_input": tool_input,
                "prompt": prompt,
                "user_id": user_id,
            },
        )

        self.assertEqual(
            build_tool_observation_entry(
                name="task_plan",
                output=None,
                registration=registration,
                step_tool_meta={
                    "name": "task_plan",
                    "label": "Task Planner",
                    "status": "done",
                    "output_preview": {
                        "plan": "Analyze request -> Synthesize final answer",
                    },
                },
            ),
            "Task Planner: Planned steps - Analyze request -> Synthesize final answer.",
        )

    def test_build_tool_observation_entry_infers_result_summary_from_step_meta_safe_output_without_registration(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="hosted_search",
                output=None,
                step_tool_meta={
                    "name": "hosted_search",
                    "label": "Hosted Search",
                    "status": "done",
                    "semantic_kind": "provider_search",
                    "semantic_family": "knowledge_retrieval",
                    "effective_result_output_keys": [
                        "documents_total",
                        "request_id",
                    ],
                    "output": {
                        "documents_total": 2,
                        "request_id": "req-1",
                        "documents": [{"id": "doc-1"}],
                    },
                    "output_preview": {
                        "documents_total": 2,
                    },
                },
            ),
            "Hosted Search: Retrieved 2 documents (request id req-1).",
        )

    def test_build_tool_observation_entry_infers_result_summary_from_step_meta_preview_without_registration(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="provider_planner",
                output=None,
                step_tool_meta={
                    "name": "provider_planner",
                    "label": "Provider Planner",
                    "status": "done",
                    "semantic_kind": "provider_planner",
                    "semantic_family": "task_planner",
                    "output_preview": {
                        "plan": "Analyze request -> Synthesize final answer",
                    },
                },
            ),
            "Provider Planner: Planned steps - Analyze request -> Synthesize final answer.",
        )

    def test_build_tool_observation_entry_infers_result_summary_from_noncanonical_semantic_kind_and_output_keys_without_semantic_family(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="hosted_lookup",
                output=None,
                step_tool_meta={
                    "name": "hosted_lookup",
                    "label": "Hosted Lookup",
                    "kind": "provider_retrieval",
                    "semantic_kind": "provider_search",
                    "status": "done",
                    "effective_result_output_keys": [
                        "documents_total",
                        "request_id",
                    ],
                    "output": {
                        "documents_total": 2,
                        "request_id": "req-1",
                        "documents": [{"id": "doc-1"}],
                    },
                    "output_preview": {
                        "documents_total": 2,
                    },
                },
            ),
            "Hosted Lookup: Retrieved 2 documents (request id req-1).",
        )

    def test_build_tool_observation_entry_infers_calc_summary_from_noncanonical_semantic_kind_and_output_keys_without_semantic_family(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="hosted_math",
                output=None,
                step_tool_meta={
                    "name": "hosted_math",
                    "label": "Hosted Math",
                    "kind": "provider_calc",
                    "semantic_kind": "provider_math",
                    "status": "done",
                    "effective_result_output_keys": [
                        "result",
                        "request_id",
                    ],
                    "output": {
                        "result": 7,
                        "request_id": "req-calc-1",
                    },
                    "output_preview": {
                        "result": 7,
                    },
                },
            ),
            "Hosted Math: Calculated result = 7 (request id req-calc-1).",
        )

    def test_build_tool_observation_entry_does_not_imply_local_kb_for_name_only_real_tool_without_registration(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="provider_search",
                output=None,
                step_tool_meta={
                    "name": "provider_search",
                    "label": "Provider Search",
                    "status": "done",
                    "effective_result_output_keys": [
                        "hit_count",
                        "knowledge_base_id",
                        "request_id",
                    ],
                    "output": {
                        "hit_count": 2,
                        "knowledge_base_id": "provider-kb",
                        "request_id": "req-1",
                    },
                    "output_preview": {
                        "hit_count": 2,
                        "knowledge_base_id": "provider-kb",
                    },
                },
            ),
            "Provider Search: Retrieved 2 hits (request id req-1).",
        )

    def test_build_tool_observation_entry_normalizes_numeric_string_counts_from_step_meta_output(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="provider_search",
                output=None,
                step_tool_meta={
                    "name": "provider_search",
                    "label": "Provider Search",
                    "kind": "provider_retrieval",
                    "semantic_kind": "provider_search",
                    "status": "done",
                    "effective_result_output_keys": [
                        "hit_count",
                        "knowledge_base_id",
                        "request_id",
                    ],
                    "output": {
                        "hit_count": "2",
                        "knowledge_base_id": "provider-kb",
                        "request_id": "req-string-count-1",
                    },
                    "output_preview": {
                        "hit_count": "2",
                        "knowledge_base_id": "provider-kb",
                    },
                },
            ),
            "Provider Search: Retrieved 2 hits (request id req-string-count-1).",
        )

    def test_build_tool_observation_entry_normalizes_http_json_aliases_from_step_meta_output_without_registration(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="provider_search",
                output=None,
                step_tool_meta={
                    "name": "provider_search",
                    "label": "Provider Search",
                    "kind": "provider_retrieval",
                    "semantic_kind": "provider_search",
                    "semantic_family": "knowledge_retrieval",
                    "execution_kind": "http_json",
                    "status": "done",
                    "effective_result_output_keys": [
                        "hit_count",
                        "knowledge_base_id",
                        "request_id",
                    ],
                    "output": {
                        "hit_count": "unknown",
                        "matches": [
                            {"id": "vec-1"},
                            {"id": "vec-2"},
                        ],
                        "knowledge_base_id": "provider-kb",
                        "request_id": "req-step-matches-1",
                    },
                },
            ),
            "Provider Search: Retrieved 2 hits (request id req-step-matches-1).",
        )

    def test_build_tool_observation_entry_normalizes_http_json_aliases_from_step_meta_preview_without_registration(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="provider_search",
                output=None,
                step_tool_meta={
                    "name": "provider_search",
                    "label": "Provider Search",
                    "kind": "provider_retrieval",
                    "semantic_kind": "provider_search",
                    "semantic_family": "knowledge_retrieval",
                    "execution_kind": "http_json",
                    "status": "done",
                    "output_preview": {
                        "items": [
                            {"id": "doc-1"},
                            {"id": "doc-2"},
                        ],
                        "request_id": "req-step-items-1",
                    },
                },
            ),
            "Provider Search: Retrieved 2 documents (request id req-step-items-1).",
        )

    def test_build_tool_observation_entry_does_not_imply_local_kb_for_productized_retrieval_label_without_registration(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="provider_search",
                output=None,
                step_tool_meta={
                    "name": "provider_search",
                    "label": "Provider Search [retrieval]",
                    "status": "done",
                    "effective_result_output_keys": [
                        "hit_count",
                        "knowledge_base_id",
                        "request_id",
                    ],
                    "output": {
                        "hit_count": 2,
                        "knowledge_base_id": "provider-kb",
                        "request_id": "req-1",
                    },
                    "output_preview": {
                        "hit_count": 2,
                        "knowledge_base_id": "provider-kb",
                    },
                },
            ),
            "Provider Search [retrieval]: Retrieved 2 hits (request id req-1).",
        )

    def test_build_tool_observation_entry_infers_calc_summary_for_name_only_real_tool_without_registration(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="hosted_math",
                output=None,
                step_tool_meta={
                    "name": "hosted_math",
                    "label": "Hosted Math",
                    "status": "done",
                    "effective_result_output_keys": [
                        "result",
                        "request_id",
                    ],
                    "output": {
                        "result": 7,
                        "request_id": "req-calc-1",
                    },
                    "output_preview": {
                        "result": 7,
                    },
                },
            ),
            "Hosted Math: Calculated result = 7 (request id req-calc-1).",
        )

    def test_build_tool_observation_entry_infers_calc_summary_for_productized_calculator_label_without_registration(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="custom_math_runner",
                output=None,
                step_tool_meta={
                    "name": "custom_math_runner",
                    "label": "Hosted Math [calculator]",
                    "status": "done",
                    "effective_result_output_keys": [
                        "result",
                        "request_id",
                    ],
                    "output": {
                        "result": 7,
                        "request_id": "req-calc-1",
                    },
                    "output_preview": {
                        "result": 7,
                    },
                },
            ),
            "Hosted Math [calculator]: Calculated result = 7 (request id req-calc-1).",
        )

    def test_build_tool_observation_entry_reuses_step_meta_preview_without_output(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="custom_lookup",
                output=None,
                step_tool_meta={
                    "name": "custom_lookup",
                    "label": "Custom Lookup",
                    "status": "done",
                    "output_preview": {
                        "tool_kind": "custom_lookup",
                        "hit_count": 1,
                    },
                },
            ),
            'Custom Lookup: {"tool_kind": "custom_lookup", "hit_count": 1}',
        )

    def test_build_tool_observation_entry_redacts_http_json_step_meta_preview_fallback(
        self,
    ) -> None:
        observation = build_tool_observation_entry(
            name="provider_status",
            output=None,
            step_tool_meta={
                "name": "provider_status",
                "label": "Provider Status",
                "status": "done",
                "execution_kind": "http_json",
                "output_preview": {
                    "status": "ready",
                    "access_token": "hidden",
                    "message": "gateway token=hidden",
                    "request_id": "Bearer secret-token",
                },
            },
        )

        self.assertEqual(
            observation,
            'Provider Status: {"status": "ready", "access_token": "[redacted]", "message": "gateway token=[redacted]"}',
        )
        self.assertNotIn("Bearer", observation)
        self.assertNotIn("secret-token", observation)
        self.assertNotIn("hidden", observation)

    def test_build_tool_observation_entry_redacts_malformed_http_json_step_meta_preview(
        self,
    ) -> None:
        observation = build_tool_observation_entry(
            name="provider_status",
            output=None,
            step_tool_meta={
                "name": "provider_status",
                "label": "Provider Status",
                "status": "done",
                "execution_kind": "http_json",
                "output_preview": (
                    "status=ready token=hidden "
                    "query_params.access_token Bearer secret-token"
                ),
            },
        )

        self.assertEqual(
            observation,
            'Provider Status: "status=ready [redacted] [redacted] [redacted]"',
        )
        self.assertNotIn("token=hidden", observation)
        self.assertNotIn("access_token", observation)
        self.assertNotIn("Bearer", observation)
        self.assertNotIn("secret-token", observation)

    def test_build_tool_observation_entry_redacts_http_json_direct_output_fallback(
        self,
    ) -> None:
        observation = build_tool_observation_entry(
            name="provider_status",
            output={
                "status": "ready",
                "api_key": "sk-hidden",
                "message": "gateway secret=hidden",
                "request_id": "Bearer secret-token",
            },
            step_tool_meta={
                "name": "provider_status",
                "label": "Provider Status",
                "status": "done",
                "execution_kind": "http_json",
            },
        )

        self.assertEqual(
            observation,
            'Provider Status: {"status": "ready", "api_key": "[redacted]", "message": "gateway secret=[redacted]"}',
        )
        self.assertNotIn("Bearer", observation)
        self.assertNotIn("secret-token", observation)
        self.assertNotIn("sk-hidden", observation)
        self.assertNotIn("hidden", observation)

    def test_build_tool_result_summary_redacts_generic_payload_sensitive_fields(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_status",
            kind="provider_status",
            label="Provider Status",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            result_output_keys=("status", "message", "access_token"),
            runner=lambda *, tool_input, prompt, user_id: {},
        )

        summary = build_tool_result_summary(
            name="provider_status",
            output={
                "status": "ready",
                "message": "gateway token=hidden",
                "access_token": "hidden",
            },
            registration=registration,
        )

        self.assertEqual(
            summary,
            "Provider Status output - status=ready, message=gateway [redacted].",
        )
        self.assertNotIn("access_token", summary or "")
        self.assertNotIn("hidden", summary or "")

    def test_build_tool_observation_entry_infers_summary_from_json_string_step_meta_preview_without_output(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="hosted_math",
                output=None,
                step_tool_meta={
                    "name": "hosted_math",
                    "label": "Hosted Math",
                    "status": "done",
                    "output_preview": '{"result":7,"request_id":"req-calc-1"}',
                },
            ),
            "Hosted Math: Calculated result = 7 (request id req-calc-1).",
        )

    def test_build_tool_observation_entry_infers_summary_from_json_string_step_meta_safe_output_without_output(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="hosted_math",
                output=None,
                step_tool_meta={
                    "name": "hosted_math",
                    "label": "Hosted Math",
                    "status": "done",
                    "effective_result_output_keys": [
                        "result",
                        "request_id",
                    ],
                    "output": '{"result":7,"request_id":"req-calc-1","kind":"provider_calc","secret":"hidden"}',
                },
            ),
            "Hosted Math: Calculated result = 7 (request id req-calc-1).",
        )

    def test_build_tool_observation_entry_infers_summary_from_quoted_json_string_step_meta_safe_output_without_output(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="hosted_math",
                output=None,
                step_tool_meta={
                    "name": "hosted_math",
                    "label": "Hosted Math",
                    "status": "done",
                    "effective_result_output_keys": [
                        "result",
                        "request_id",
                    ],
                    "output": json.dumps(
                        '{"result":7,"request_id":"req-calc-1","secret":"hidden"}'
                    ),
                },
            ),
            "Hosted Math: Calculated result = 7 (request id req-calc-1).",
        )

    def test_build_tool_observation_entry_accepts_tuple_effective_result_output_keys_from_step_meta(
        self,
    ) -> None:
        self.assertEqual(
            build_tool_observation_entry(
                name="custom_lookup",
                output={
                    "tool_kind": "custom_lookup",
                    "hit_count": 1,
                    "secret": "do-not-preview",
                },
                step_tool_meta={
                    "name": "custom_lookup",
                    "label": "Custom Lookup",
                    "status": "done",
                    "effective_result_output_keys": (
                        "tool_kind",
                        "hit_count",
                    ),
                    "output": {
                        "tool_kind": "custom_lookup",
                        "hit_count": 1,
                        "secret": "do-not-preview",
                    },
                },
            ),
            'Custom Lookup: {"tool_kind": "custom_lookup", "hit_count": 1}',
        )

    def test_get_trace_step_display_content_prefers_tool_result_summary_over_generic_done_content(
        self,
    ) -> None:
        step = SimpleNamespace(
            id="step-provider-search-summary",
            seq=4,
            type="action",
            content="Tool done: Provider Search",
            meta=SimpleNamespace(
                tool={
                    "name": "provider_search",
                    "label": "Provider Search",
                    "status": "done",
                    "result_summary": "Retrieved 2 documents (request id req-1).",
                    "effective_result_preview_keys": ["documents_total"],
                    "effective_result_output_keys": ["documents_total", "request_id"],
                    "output_preview": {"documents_total": 2},
                    "output": {
                        "documents_total": 2,
                        "request_id": "req-1",
                    },
                }
            ),
        )

        content = chat_persistence_module.get_trace_step_display_content(step)

        self.assertEqual(
            content,
            'Retrieved 2 documents (request id req-1).\nPreview: {"documents_total":2}\nOutput: {"documents_total":2,"request_id":"req-1"}',
        )
        self.assertNotIn("Tool done: Provider Search", content)

    def test_get_trace_step_display_content_infers_result_summary_from_json_string_output_preview(
        self,
    ) -> None:
        step = SimpleNamespace(
            id="step-hosted-math-preview-string",
            seq=5,
            type="action",
            content="Tool done: Hosted Math",
            meta=SimpleNamespace(
                tool={
                    "name": "hosted_math",
                    "label": "Hosted Math",
                    "status": "done",
                    "output_preview": '{"result":7,"request_id":"req-calc-1"}',
                }
            ),
        )

        content = chat_persistence_module.get_trace_step_display_content(step)

        self.assertEqual(
            content,
            'Calculated result = 7 (request id req-calc-1).\nPreview: {"result":7,"request_id":"req-calc-1"}',
        )
        self.assertNotIn("Tool done: Hosted Math", content)

    def test_get_trace_step_display_content_infers_result_summary_from_quoted_json_string_output_preview(
        self,
    ) -> None:
        step = SimpleNamespace(
            id="step-hosted-math-preview-quoted-string",
            seq=5,
            type="action",
            content="Tool done: Hosted Math",
            meta=SimpleNamespace(
                tool={
                    "name": "hosted_math",
                    "label": "Hosted Math",
                    "status": "done",
                    "output_preview": json.dumps(
                        '{"result":7,"request_id":"req-calc-1"}'
                    ),
                }
            ),
        )

        content = chat_persistence_module.get_trace_step_display_content(step)

        self.assertEqual(
            content,
            'Calculated result = 7 (request id req-calc-1).\nPreview: {"result":7,"request_id":"req-calc-1"}',
        )
        self.assertNotIn("Tool done: Hosted Math", content)
        self.assertNotIn('\\"result\\"', content)

    def test_get_trace_step_display_content_infers_planner_summary_from_wrapped_output(
        self,
    ) -> None:
        step = SimpleNamespace(
            id="step-hosted-planner-wrapped-output",
            seq=5,
            type="action",
            content="Tool done: Hosted Planner",
            meta=SimpleNamespace(
                tool={
                    "name": "hosted_planner_gateway",
                    "label": "Hosted Planner",
                    "semantic_kind": UserString("hosted_planner_gateway"),
                    "semantic_family": UserString("task_planner"),
                    "status": "done",
                    "effective_result_output_keys": UserList(
                        [UserString("plan"), UserString("steps")]
                    ),
                    "output": {
                        "plan": UserString("gather -> calculate"),
                        "steps": UserList(
                            [UserString("gather"), UserString("calculate")]
                        ),
                    },
                }
            ),
        )

        content = chat_persistence_module.get_trace_step_display_content(step)

        self.assertEqual(
            content,
            'Planned steps - gather -> calculate.\nOutput: {"plan":"gather -> calculate","steps":["gather","calculate"]}',
        )
        self.assertNotIn("Tool done: Hosted Planner", content)

    def test_get_trace_step_markdown_meta_backfills_planner_summary_from_wrapped_output(
        self,
    ) -> None:
        class WrappedMeta:
            def model_dump(self, *, exclude_none: bool = True) -> dict[str, object]:
                del exclude_none
                return {
                    "tool": {
                        "name": "hosted_planner_gateway",
                        "label": "Hosted Planner",
                        "semantic_kind": UserString("hosted_planner_gateway"),
                        "semantic_family": UserString("task_planner"),
                        "status": "done",
                        "effective_result_output_keys": UserList(
                            [UserString("plan"), UserString("steps")]
                        ),
                        "output": {
                            "steps": UserList(
                                [UserString("gather"), UserString("calculate")]
                            ),
                        },
                    }
                }

        step = SimpleNamespace(
            id="step-hosted-planner-wrapped-meta",
            seq=5,
            type="action",
            content="Tool done: Hosted Planner",
            meta=WrappedMeta(),
        )

        markdown_meta = chat_persistence_module.get_trace_step_markdown_meta(step)

        self.assertIsNotNone(markdown_meta)
        self.assertEqual(
            markdown_meta["tool"]["result_summary"],  # type: ignore[index]
            "Planned steps - gather -> calculate.",
        )

    def test_get_trace_step_display_content_infers_retrieval_result_summary_from_safe_output_without_explicit_result_summary(
        self,
    ) -> None:
        step = SimpleNamespace(
            id="step-provider-search-summary-inferred",
            seq=5,
            type="action",
            content="Tool done: Provider Search",
            meta=SimpleNamespace(
                tool={
                    "name": "provider_search",
                    "label": "Provider Search",
                    "kind": "provider_retrieval",
                    "semantic_kind": "provider_search",
                    "semantic_family": "knowledge_retrieval",
                    "status": "done",
                    "effective_result_preview_keys": [
                        "hit_count",
                        "knowledge_base_id",
                    ],
                    "effective_result_output_keys": [
                        "hit_count",
                        "knowledge_base_id",
                        "request_id",
                    ],
                    "output_preview": {
                        "hit_count": 2,
                        "knowledge_base_id": "provider-kb",
                    },
                    "output": {
                        "hit_count": 2,
                        "knowledge_base_id": "provider-kb",
                        "request_id": "req-1",
                    },
                }
            ),
        )

        content = chat_persistence_module.get_trace_step_display_content(step)

        self.assertEqual(
            content,
            'Retrieved 2 hits (request id req-1).\nPreview: {"hit_count":2,"knowledge_base_id":"provider-kb"}\nOutput: {"hit_count":2,"knowledge_base_id":"provider-kb","request_id":"req-1"}',
        )
        self.assertNotIn("Tool done: Provider Search", content)

    def test_get_trace_step_display_content_infers_calc_result_summary_from_safe_output_without_explicit_result_summary(
        self,
    ) -> None:
        step = SimpleNamespace(
            id="step-provider-math-summary-inferred",
            seq=6,
            type="action",
            content="Tool done: Provider Math",
            meta=SimpleNamespace(
                tool={
                    "name": "provider_math",
                    "label": "Provider Math",
                    "kind": "provider_calc",
                    "semantic_kind": "local_calculator",
                    "status": "done",
                    "effective_result_preview_keys": ["result"],
                    "effective_result_output_keys": ["result", "request_id"],
                    "output_preview": {
                        "result": 7,
                    },
                    "output": {
                        "result": 7,
                        "request_id": "req-calc-1",
                    },
                }
            ),
        )

        content = chat_persistence_module.get_trace_step_display_content(step)

        self.assertEqual(
            content,
            'Calculated result = 7 (request id req-calc-1).\nPreview: {"result":7}\nOutput: {"result":7,"request_id":"req-calc-1"}',
        )
        self.assertNotIn("Tool done: Provider Math", content)

    def test_get_trace_step_display_content_drops_unsafe_request_id_from_old_safe_output(
        self,
    ) -> None:
        step = SimpleNamespace(
            id="step-provider-math-unsafe-request-id",
            seq=7,
            type="action",
            content="Tool done: Provider Math",
            meta=SimpleNamespace(
                tool={
                    "name": "provider_math",
                    "label": "Provider Math",
                    "kind": "provider_calc",
                    "semantic_kind": "local_calculator",
                    "status": "done",
                    "effective_result_preview_keys": ["result"],
                    "effective_result_output_keys": ["result", "request_id"],
                    "output_preview": {
                        "result": 7,
                    },
                    "output": {
                        "result": 7,
                        "request_id": "Bearer secret-token",
                    },
                }
            ),
        )

        content = chat_persistence_module.get_trace_step_display_content(step)

        self.assertEqual(
            content,
            'Calculated result = 7.\nPreview: {"result":7}',
        )
        self.assertNotIn("Bearer", content)
        self.assertNotIn("secret-token", content)

    def test_get_trace_step_display_content_appends_tool_registry_diagnostics_entries(
        self,
    ) -> None:
        step = SimpleNamespace(
            id="step-tool-registry-diagnostics",
            seq=5,
            type="observation",
            content="Tool registry diagnostics: source=file_source skipped=1 missing=1",
            meta=SimpleNamespace(
                tool_registry={
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
                            "values": ("/tmp/missing-registry.json",),
                        },
                    ),
                }
            ),
        )

        content = chat_persistence_module.get_trace_step_display_content(step)

        self.assertEqual(
            content,
            "Tool registry diagnostics: source=file_source skipped=1 missing=1\n"
            "skipped registry sources: planning_suite\n"
            "missing registry files: /tmp/missing-registry.json",
        )

    def test_get_trace_step_display_content_redacts_tool_registry_diagnostics_values(
        self,
    ) -> None:
        step = SimpleNamespace(
            id="step-tool-registry-diagnostics-sensitive",
            seq=5,
            type="observation",
            content="Tool registry diagnostics: source=file_source skipped=0 missing=0",
            meta=SimpleNamespace(
                tool_registry={
                    "provider_source": "file_source",
                    "has_diagnostics": True,
                    "skipped_total": 0,
                    "missing_total": 0,
                    "total": 1,
                    "entries": (
                        {
                            "kind": "invalid",
                            "target": "tool_executions",
                            "count": 1,
                            "values": (
                                "provider_status: unsupported tool execution kind token=hidden",
                            ),
                        },
                    ),
                }
            ),
        )

        content = chat_persistence_module.get_trace_step_display_content(step)

        self.assertEqual(
            content,
            "Tool registry diagnostics: source=file_source skipped=0 missing=0\n"
            "invalid tool executions: "
            "provider_status: unsupported tool execution kind [redacted]",
        )
        self.assertNotIn("token=hidden", content)

    def test_build_tool_step_updates_and_observation_use_display_label_for_mock_plan(
        self,
    ) -> None:
        base_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool running: Task Planner",
            "meta": {
                "model": "mock-gpt",
                "step_type": "tool_call",
                "label": "tool_1",
                "retryCount": 0,
                "tokens": 5,
                "cost_estimate": None,
                "tool": {
                    "name": "mock_plan",
                    "label": "Task Planner",
                    "input": {"prompt_preview": "请帮我规划"},
                    "status": "running",
                    "retry_count": 0,
                },
            },
        }
        output = {
            "plan": "Analyze request -> retrieve context -> synthesize answer.",
            "echo": True,
        }

        success_step = build_tool_step_success_update(
            action_step=base_step,
            name="mock_plan",
            tool_input={"prompt_preview": "请帮我规划"},
            output=output,
            retry_count=0,
            token_count=7,
            last_error=None,
        )

        self.assertEqual(success_step["content"], "Tool done: Task Planner")
        self.assertEqual(success_step["meta"]["tool"]["label"], "Task Planner")
        self.assertEqual(
            build_tool_observation_entry(name="mock_plan", output=output),
            'Task Planner: {"plan": "Analyze request -> retrieve context -> synthesize answer."}',
        )

    def test_build_tool_step_updates_observation_and_rag_followup_use_display_label_for_mock_retrieve(
        self,
    ) -> None:
        base_step = {
            "id": "step-2",
            "seq": 4,
            "type": "action",
            "content": "Tool running: Knowledge Retrieval",
            "meta": {
                "model": "mock-gpt",
                "step_type": "tool_call",
                "label": "tool_2",
                "retryCount": 0,
                "tokens": 5,
                "cost_estimate": None,
                "tool": {
                    "name": "mock_retrieve",
                    "label": "Knowledge Retrieval",
                    "input": {"query": "检索 demo"},
                    "status": "running",
                    "retry_count": 0,
                },
            },
        }
        output = {
            "chunks": ["alpha", "beta"],
            "knowledge_base_id": "demo-kb",
            "hit_count": 2,
        }

        success_step = build_tool_step_success_update(
            action_step=base_step,
            name="mock_retrieve",
            tool_input={"query": "检索 demo"},
            output=output,
            retry_count=0,
            token_count=7,
            last_error=None,
        )
        rag_followup = build_tool_rag_followup(
            task_id="task-1",
            step_id="rag-1",
            seq=5,
            model="mock-gpt",
            tool_name="mock_retrieve",
            output=output,
            token_count=2,
        )

        self.assertEqual(success_step["content"], "Tool done: Knowledge Retrieval")
        self.assertEqual(success_step["meta"]["tool"]["name"], "task_retrieve")
        self.assertEqual(
            build_tool_observation_entry(name="mock_retrieve", output=output),
            'Knowledge Retrieval: {"hit_count": 2, "knowledge_base_id": "demo-kb"}',
        )
        self.assertIsNotNone(rag_followup)
        assert rag_followup is not None
        self.assertEqual(
            rag_followup["step"]["content"],
            "Knowledge Retrieval returned snippets from the selected knowledge base.",
        )

    def test_build_tool_trace_event_keeps_current_shape(self) -> None:
        step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool done: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "done",
                }
            },
        }

        self.assertEqual(
            build_tool_trace_event(
                task_id="task-1",
                step_id="step-1",
                step=step,
            ),
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": step,
            },
        )

    def test_build_tool_trace_event_redacts_http_json_step_output_payloads(self) -> None:
        step = {
            "id": "step-http-json-trace-output",
            "seq": 4,
            "type": "action",
            "content": "Tool done: Provider Status",
            "meta": {
                "tool": {
                    "name": "provider_status",
                    "label": "Provider Status",
                    "status": "done",
                    "execution_kind": "http_json",
                    "effective_result_output_keys": ["status", "message"],
                    "output": {
                        "status": "ready",
                        "message": "gateway token=hidden",
                        "access_token": "secret-token",
                        "request_id": "Bearer secret-token",
                    },
                    "output_preview": {
                        "status": "ready",
                        "message": "preview token=hidden",
                        "access_token": "secret-token",
                        "request_id": "Bearer secret-token",
                    },
                }
            },
        }

        event = build_tool_trace_event(
            task_id="task-1",
            step_id="step-http-json-trace-output",
            step=step,
        )

        tool_meta = event["step"]["meta"]["tool"]
        self.assertEqual(
            tool_meta["output"],
            {
                "status": "ready",
                "message": "gateway token=[redacted]",
            },
        )
        self.assertEqual(
            tool_meta["output_preview"],
            {
                "status": "ready",
                "message": "preview token=[redacted]",
                "access_token": "[redacted]",
            },
        )
        serialized = json.dumps(event, ensure_ascii=False)
        self.assertNotIn("Bearer", serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("token=hidden", serialized)

    def test_build_tool_terminal_failure_transition_keeps_current_shape(self) -> None:
        step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool error: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "error",
                }
            },
        }

        transition = build_tool_terminal_failure_transition(
            task_id="task-1",
            step_id="step-1",
            action_step=step,
            error_message="transient",
            retry_count=1,
        )

        self.assertEqual(
            transition["trace"],
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": step,
            },
        )
        self.assertEqual(
            transition["audit_detail"],
            {
                "step_id": "step-1",
                "retry_count": 1,
            },
        )
        self.assertEqual(
            transition["state"],
            {
                "task_id": "task-1",
                "phase": "error",
            },
        )
        self.assertEqual(transition["status"], "failed")
        self.assertEqual(transition["error_message"], "transient")

    def test_build_tool_terminal_failure_transition_redacts_raw_diagnostics_payload(
        self,
    ) -> None:
        step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": (
                "provider_search: unsupported tool execution kind api_key=hidden"
            ),
            "meta": {
                "tool": {
                    "name": "provider_search",
                    "status": "error",
                    "error": (
                        "provider_search: http_json execution query_params.access_token must be safe"
                    ),
                }
            },
        }

        transition = build_tool_terminal_failure_transition(
            task_id="task-1",
            step_id="step-1",
            action_step=step,
            error_message="provider_search failed with token=hidden",
            retry_count=1,
        )

        serialized = json.dumps(transition, default=str)
        self.assertNotIn("api_key=hidden", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertIn("unsupported tool execution kind [redacted]", serialized)
        self.assertIn("http_json execution [redacted] must be safe", serialized)
        self.assertIn("provider_search failed with [redacted]", serialized)

    def test_build_tool_rag_step_keeps_current_shape(self) -> None:
        self.assertEqual(
            build_tool_rag_step(
                step_id="rag-1",
                seq=4,
                model="mock-gpt",
                chunks=["a", "b"],
                knowledge_base_id="demo",
                token_count=2,
            ),
            {
                "id": "rag-1",
                "seq": 4,
                "type": "thought",
                "content": "Knowledge Retrieval returned snippets from the selected knowledge base.",
                "meta": {
                    "model": "mock-gpt",
                    "step_type": "rag_retrieval",
                    "tokens": 2,
                    "cost_estimate": None,
                    "rag": {
                        "chunks": ["a", "b"],
                        "knowledge_base_id": "demo",
                    },
                },
            },
        )

    def test_build_tool_prompt_with_observations_keeps_current_shape(self) -> None:
        self.assertEqual(
            build_tool_prompt_with_observations(
                prompt="hello",
                tool_observations=[],
            ),
            "hello",
        )
        self.assertEqual(
            build_tool_prompt_with_observations(
                prompt="hello",
                tool_observations=["calc_eval: {\"result\": 7.0}"],
            ),
            'hello\n\nTool observations:\ncalc_eval: {"result": 7.0}',
        )

    def test_build_tool_attempt_result_keeps_success_shape(self) -> None:
        step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool done: calc_eval",
            "meta": {
                "tool": {
                    "name": "calc_eval",
                    "status": "done",
                    "output": {"result": 7.0},
                }
            },
        }

        self.assertEqual(
            build_tool_attempt_result(
                outcome="success",
                action_step=step,
                events={
                    "tool_end": {
                        "task_id": "task-1",
                        "step_id": "step-1",
                        "status": "done",
                    }
                },
                retryable=False,
                error_message=None,
                retry_count=0,
            ),
            {
                "outcome": "success",
                "action_step": step,
                "events": {
                    "tool_end": {
                        "task_id": "task-1",
                        "step_id": "step-1",
                        "status": "done",
                    }
                },
                "retryable": False,
                "error_message": None,
                "retry_count": 0,
            },
        )

    def test_build_tool_attempt_result_redacts_error_payload(self) -> None:
        step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": (
                "provider_search: unsupported tool execution kind api_key=hidden"
            ),
            "meta": {
                "tool": {
                    "name": "provider_search",
                    "status": "error",
                    "error": (
                        "provider_search: http_json execution query_params.access_token must be safe"
                    ),
                }
            },
        }

        result = build_tool_attempt_result(
            outcome="error",
            action_step=step,
            events={
                "tool_end": {
                    "task_id": "task-1",
                    "step_id": "step-1",
                    "status": "error",
                    "error": "headers.x-api-key is invalid",
                },
                "error": {
                    "task_id": "task-1",
                    "message": "provider_search failed with token=hidden",
                    "code": "tool_execution_error",
                },
            },
            retryable=False,
            error_message="provider_search failed with token=hidden",
            retry_count=1,
        )

        serialized = json.dumps(result, default=str)
        self.assertNotIn("api_key=hidden", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("x-api-key", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertIn("unsupported tool execution kind [redacted]", serialized)
        self.assertIn("http_json execution [redacted] must be safe", serialized)
        self.assertIn("provider_search failed with [redacted]", serialized)

    def test_build_tool_attempt_outcome_keeps_success_shape(self) -> None:
        base_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool running: calc_eval",
            "meta": {
                "model": "mock-gpt",
                "step_type": "tool_call",
                "label": "tool_1",
                "retryCount": 0,
                "tokens": 5,
                "cost_estimate": None,
                "tool": {
                    "name": "calc_eval",
                    "input": {"expression": "1+2*3"},
                    "status": "running",
                    "retry_count": 0,
                },
            },
        }
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "local_calculator",
        }

        outcome = build_tool_attempt_outcome(
            task_id="task-1",
            step_id="step-1",
            action_step=base_step,
            runtime_ctx=build_tool_runtime_context(
                name="calc_eval",
                prompt="calc",
                user_id="user-1",
                attempt=0,
            ),
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=output,
            exc=None,
            token_count=7,
            last_error=None,
        )

        self.assertEqual(outcome["outcome"], "success")
        self.assertFalse(outcome["retryable"])
        self.assertIsNone(outcome["error_message"])
        self.assertEqual(outcome["retry_count"], 0)
        self.assertEqual(outcome["action_step"]["content"], "Tool done: Calculator")
        self.assertEqual(outcome["events"]["tool_end"]["status"], "done")

    def test_build_tool_attempt_outcome_keeps_error_shape(self) -> None:
        base_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool running: calc_eval",
            "meta": {
                "model": "mock-gpt",
                "step_type": "tool_call",
                "label": "tool_1",
                "retryCount": 0,
                "tokens": 5,
                "cost_estimate": None,
                "tool": {
                    "name": "calc_eval",
                    "input": {"expression": "1+2*3"},
                    "status": "running",
                    "retry_count": 0,
                },
            },
        }
        ctx = build_tool_runtime_context(
            name="calc_eval",
            prompt="calc",
            user_id="user-1",
            attempt=0,
        )

        outcome = build_tool_attempt_outcome(
            task_id="task-1",
            step_id="step-1",
            action_step=base_step,
            runtime_ctx=ctx,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output=None,
            exc=MockToolExecutionError("transient", fatal=False),
            token_count=9,
            last_error=None,
        )

        self.assertEqual(outcome["outcome"], "error")
        self.assertTrue(outcome["retryable"])
        self.assertEqual(outcome["error_message"], "transient")
        self.assertEqual(outcome["retry_count"], 1)
        self.assertEqual(outcome["action_step"]["content"], "Tool error: Calculator")
        self.assertEqual(outcome["events"]["tool_end"]["status"], "error")

    def test_build_tool_attempt_outcome_redacts_error_payload(self) -> None:
        registration = ToolRegistration(
            name="provider_search",
            kind="provider_retrieval",
            label="Provider Search",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            runner=lambda *, tool_input, prompt, user_id: {},
            execution_kind="http_json",
        )
        registry = {"provider_search": registration}
        base_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool running: Provider Search",
            "meta": {
                "model": "mock-gpt",
                "step_type": "tool_call",
                "legacy_error": (
                    "provider_search: http_json execution json_body.client_secret must be safe"
                ),
                "tool": {
                    "name": "provider_search",
                    "status": "running",
                },
            },
        }

        outcome = build_tool_attempt_outcome(
            task_id="task-1",
            step_id="step-1",
            action_step=base_step,
            runtime_ctx=build_tool_runtime_context(
                name="provider_search",
                prompt="search",
                user_id="user-1",
                attempt=0,
                registry=registry,
            ),
            name="provider_search",
            tool_input={"query": "demo"},
            output=None,
            exc=MockToolExecutionError("provider_search failed with token=hidden", fatal=True),
            token_count=9,
            last_error=None,
            registry=registry,
        )

        serialized = json.dumps(outcome, default=str)
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("token=hidden", serialized)
        self.assertIn("http_json execution [redacted] must be safe", serialized)
        self.assertIn("provider_search failed with [redacted]", serialized)

    def test_build_tool_attempt_outcome_honors_runtime_preview_policy(self) -> None:
        base_step = {
            "id": "step-1",
            "seq": 3,
            "type": "action",
            "content": "Tool running: Custom Lookup",
            "meta": {
                "model": "mock-gpt",
                "step_type": "tool_call",
                "label": "tool_1",
                "retryCount": 0,
                "tokens": 5,
                "cost_estimate": None,
                "tool": {
                    "name": "custom_lookup",
                    "label": "Custom Lookup",
                    "input": {"query": "secret"},
                    "status": "running",
                    "retry_count": 0,
                },
            },
        }
        registry = {
            "custom_lookup": ToolRegistration(
                name="custom_lookup",
                kind="custom_lookup",
                label="Custom Lookup",
                retryable_by_default=False,
                default_timeout_ms=12_000,
                requires_user_context=False,
                supports_result_preview=False,
                runner=lambda *, tool_input, prompt, user_id: {
                    "documents": [{"title": "Secret"}],
                    "tool_kind": "custom_lookup",
                },
            )
        }

        outcome = build_tool_attempt_outcome(
            task_id="task-1",
            step_id="step-1",
            action_step=base_step,
            runtime_ctx=build_tool_runtime_context(
                name="custom_lookup",
                prompt="lookup",
                user_id="user-1",
                attempt=0,
                registry=registry,
            ),
            name="custom_lookup",
            tool_input={"query": "secret"},
            output={
                "documents": [{"title": "Secret"}],
                "tool_kind": "custom_lookup",
            },
            exc=None,
            token_count=7,
            last_error=None,
        )

        self.assertEqual(outcome["events"]["tool_end"]["latency_ms"], 48)
        self.assertIsNone(outcome["events"]["tool_end"]["output_preview"])

    def test_build_tool_iteration_context_keeps_current_shape(self) -> None:
        context = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
        )

        self.assertEqual(context["step_id"], "step-1")
        self.assertEqual(context["action_step"]["id"], "step-1")
        self.assertEqual(context["action_step"]["seq"], 3)
        self.assertEqual(context["action_step"]["content"], "Tool running: Calculator")
        self.assertEqual(context["action_step"]["meta"]["tool"]["status"], "running")

    def test_build_tool_iteration_context_uses_explicit_display_name_for_extra_tool(
        self,
    ) -> None:
        context = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="calc_eval_fast",
            tool_input={"expression": "1+2*3"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            display_name="Fast Calculator",
        )

        self.assertEqual(context["action_step"]["content"], "Tool running: Fast Calculator")
        self.assertEqual(
            context["action_step"]["meta"]["tool"]["label"],
            "Fast Calculator",
        )

    def test_build_tool_iteration_context_humanizes_unlabeled_real_tool_display_name(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_search",
            kind="provider_retrieval",
            label="",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=True,
            supports_result_preview=True,
            runner=lambda *, tool_input, prompt, user_id: {
                "query": str(tool_input.get("query", "")),
                "documents_total": 1,
            },
            runtime_semantic_kind="provider_search",
        )
        context = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="provider_search",
            tool_input={"query": "demo"},
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            registration=registration,
        )

        self.assertEqual(context["action_step"]["content"], "Tool running: Provider Search")
        self.assertEqual(
            context["action_step"]["meta"]["tool"]["label"],
            "Provider Search",
        )

    def test_build_tool_iteration_context_normalizes_task_plan_input_for_extra_planner_registry(
        self,
    ) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_profile="planning_only",
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "calc_eval_fast": {
                            "template": "calc_eval",
                            "label": "Fast Calculator",
                        },
                        "mock_plan_brief": {
                            "template": "mock_plan",
                            "label": "Brief Planner",
                        },
                    }
                ),
                tool_registry_overrides_json=None,
            )
        )

        context = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="task_plan",
            tool_input={
                "prompt_preview": "please plan",
                "planned_tool_names": ["mock_plan_brief", "calc_eval_fast"],
                "planned_tool_execution_kinds": ["mock", "http_json"],
            },
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            registry_provider=registry_provider,
        )

        self.assertEqual(
            context["action_step"]["meta"]["tool"]["input"],
            {
                "prompt_preview": "please plan",
                "planned_tool_names": ["calc_eval_fast"],
                "planned_tool_labels": ["Fast Calculator"],
                "planned_tool_kinds": ["local_calculator"],
                "planned_tool_execution_kinds": [""],
            },
        )

    def test_build_tool_iteration_context_normalizes_tuple_task_plan_inputs(self) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_profile="planning_only",
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "calc_eval_fast": {
                            "template": "calc_eval",
                            "label": "Fast Calculator",
                        },
                        "mock_plan_brief": {
                            "template": "mock_plan",
                            "label": "Brief Planner",
                        },
                    }
                ),
                tool_registry_overrides_json=None,
            )
        )

        context = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="task_plan",
            tool_input={
                "prompt_preview": "please plan",
                "planned_tool_names": ("mock_plan_brief", "calc_eval_fast"),
                "planned_tool_labels": ("Brief Planner", "Fast Calculator"),
            },
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            registry_provider=registry_provider,
        )

        self.assertEqual(
            context["action_step"]["meta"]["tool"]["input"],
            {
                "prompt_preview": "please plan",
                "planned_tool_names": ["calc_eval_fast"],
                "planned_tool_labels": ["Fast Calculator"],
                "planned_tool_kinds": ["local_calculator"],
                "planned_tool_execution_kinds": [""],
            },
        )

    def test_build_tool_iteration_context_normalizes_wrapped_task_plan_inputs(self) -> None:
        registry_provider = get_configured_tool_registry_provider(
            settings=SimpleNamespace(
                tool_registry_profile="planning_only",
                tool_registry_extra_tools_json=json.dumps(
                    {
                        "calc_eval_fast": {
                            "template": "calc_eval",
                            "label": "Fast Calculator",
                        },
                        "mock_plan_brief": {
                            "template": "mock_plan",
                            "label": "Brief Planner",
                        },
                    }
                ),
                tool_registry_overrides_json=None,
            )
        )

        context = build_tool_iteration_context(
            step_id="step-1",
            seq=3,
            name="task_plan",
            tool_input={
                "prompt_preview": UserString("please plan"),
                "planned_tool_names": UserList(
                    [UserString("mock_plan_brief"), UserString("calc_eval_fast")]
                ),
                "planned_tool_labels": UserList(
                    [UserString("Brief Planner"), UserString("Fast Calculator")]
                ),
            },
            model="mock-gpt",
            label="tool_1",
            token_count=5,
            registry_provider=registry_provider,
        )

        self.assertEqual(
            context["action_step"]["meta"]["tool"]["input"],
            {
                "prompt_preview": UserString("please plan"),
                "planned_tool_names": ["calc_eval_fast"],
                "planned_tool_labels": ["Fast Calculator"],
                "planned_tool_kinds": ["local_calculator"],
                "planned_tool_execution_kinds": [""],
            },
        )

    def test_build_tool_iteration_success_artifacts_use_preview_aware_observation_shape(self) -> None:
        action_step = build_tool_step_success_update(
            action_step={
                "id": "step-1",
                "seq": 3,
                "type": "action",
                "content": "Tool running: calc_eval",
                "meta": {
                    "tool": {
                        "name": "calc_eval",
                        "status": "running",
                    }
                },
            },
            name="calc_eval",
            tool_input={"expression": "1+2*3"},
            output={
                "expression": "1+2*3",
                "result": 7.0,
                "tool_kind": "local_calculator",
            },
            retry_count=0,
            token_count=7,
            last_error=None,
        )

        artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-1",
            action_step=action_step,
            name="calc_eval",
        )

        self.assertEqual(
            artifacts["trace"],
            {
                "task_id": "task-1",
                "step_id": "step-1",
                "step": action_step,
            },
        )
        self.assertEqual(
            artifacts["trace"]["step"]["meta"]["tool"]["output_preview"],
            {
                "expression": "1+2*3",
                "result": 7.0,
            },
        )
        self.assertEqual(
            artifacts["observation"],
            'Calculator: {"expression": "1+2*3", "result": 7.0}',
        )
        self.assertEqual(
            artifacts["output"],
            {
                "expression": "1+2*3",
                "result": 7.0,
                "tool_kind": "local_calculator",
            },
        )

    def test_build_tool_iteration_success_artifacts_infer_preview_shape_for_extra_provider_calc_kind(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_math",
            kind="provider_calc",
            label="Provider Math",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            runner=lambda *, tool_input, prompt, user_id: {
                "tool_input": tool_input,
                "prompt": prompt,
                "user_id": user_id,
            },
        )
        output = {
            "expression": "1+2*3",
            "result": 7.0,
            "tool_kind": "provider_calc",
            "raw_payload": {"audit": "keep-raw-only"},
        }
        action_step = build_tool_step_success_update(
            action_step={
                "id": "step-2",
                "seq": 4,
                "type": "action",
                "content": "Tool running: Provider Math",
                "meta": {
                    "tool": {
                        "name": "provider_math",
                        "label": "Provider Math",
                        "status": "running",
                    }
                },
            },
            name="provider_math",
            tool_input={"expression": "1+2*3"},
            output=output,
            retry_count=0,
            token_count=7,
            last_error=None,
            display_name="Provider Math",
            registration=registration,
        )

        artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-2",
            action_step=action_step,
            name="provider_math",
            display_name="Provider Math",
            registration=registration,
        )

        self.assertEqual(
            artifacts["trace"]["step"]["meta"]["tool"]["output_preview"],
            {
                "expression": "1+2*3",
                "result": 7.0,
            },
        )
        self.assertEqual(
            artifacts["observation"],
            "Provider Math: Calculated 1+2*3 = 7.0.",
        )
        self.assertEqual(
            artifacts["output"],
            {
                "expression": "1+2*3",
                "result": 7.0,
            },
        )

    def test_build_tool_iteration_success_artifacts_supports_registry_provider_without_explicit_display_name_or_registration(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            registry=build_tool_registry(
                overrides={
                    "provider_search": ToolRegistration(
                        name="provider_search",
                        kind="provider_retrieval",
                        label="Hosted Search",
                        retryable_by_default=True,
                        default_timeout_ms=13_000,
                        requires_user_context=True,
                        supports_result_preview=True,
                        runner=lambda *, tool_input, prompt, user_id: {
                            "documents_total": 2,
                            "tool_kind": "provider_retrieval",
                        },
                        result_preview_keys=("documents_total",),
                        runtime_semantic_kind="provider_search",
                    )
                }
            )
        )
        action_step = build_tool_step_success_update(
            action_step={
                "id": "step-2",
                "seq": 4,
                "type": "action",
                "content": "Tool running: provider_search",
                "meta": {
                    "tool": {
                        "name": "provider_search",
                        "status": "running",
                    }
                },
            },
            name="provider_search",
            tool_input={"query": "revenue trend"},
            output={
                "documents_total": 2,
                "tool_kind": "provider_retrieval",
            },
            retry_count=0,
            token_count=7,
            last_error=None,
            registry_provider=provider,
        )

        artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-2",
            action_step=action_step,
            name="provider_search",
            registry_provider=provider,
        )

        self.assertEqual(
            artifacts["observation"],
            "Hosted Search: Retrieved 2 documents.",
        )

    def test_build_tool_iteration_success_artifacts_reuses_step_meta_summary_without_registry_context(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_search",
            kind="provider_retrieval",
            label="Hosted Search",
            retryable_by_default=True,
            default_timeout_ms=13_000,
            requires_user_context=True,
            supports_result_preview=True,
            runner=lambda *, tool_input, prompt, user_id: {
                "documents_total": 2,
                "tool_kind": "provider_retrieval",
            },
            result_preview_keys=("documents_total",),
            runtime_semantic_kind="provider_search",
        )
        action_step = build_tool_step_success_update(
            action_step={
                "id": "step-2",
                "seq": 4,
                "type": "action",
                "content": "Tool running: provider_search",
                "meta": {
                    "tool": {
                        "name": "provider_search",
                        "status": "running",
                    }
                },
            },
            name="provider_search",
            tool_input={"query": "revenue trend"},
            output={
                "documents_total": 2,
                "tool_kind": "provider_retrieval",
            },
            retry_count=0,
            token_count=7,
            last_error=None,
            registration=registration,
        )

        artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-2",
            action_step=action_step,
            name="provider_search",
        )

        self.assertEqual(
            artifacts["observation"],
            "Hosted Search: Retrieved 2 documents.",
        )
        self.assertEqual(
            artifacts["output"],
            {
                "documents_total": 2,
            },
        )

    def test_build_tool_iteration_success_artifacts_infer_preview_shape_for_extra_provider_planner_kind(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_plan",
            kind="provider_planner",
            label="Provider Planner",
            retryable_by_default=False,
            default_timeout_ms=8_000,
            requires_user_context=False,
            supports_result_preview=True,
            runner=lambda *, tool_input, prompt, user_id: {
                "tool_input": tool_input,
                "prompt": prompt,
                "user_id": user_id,
            },
        )
        output = {
            "plan": "Analyze request -> Synthesize final answer",
            "steps": [
                "Analyze request",
                "Synthesize final answer",
            ],
            "tool_kind": "provider_planner",
            "raw_payload": {"audit": "keep-raw-only"},
        }
        action_step = build_tool_step_success_update(
            action_step={
                "id": "step-3",
                "seq": 5,
                "type": "action",
                "content": "Tool running: Provider Planner",
                "meta": {
                    "tool": {
                        "name": "provider_plan",
                        "label": "Provider Planner",
                        "status": "running",
                    }
                },
            },
            name="provider_plan",
            tool_input={"prompt_preview": "please plan"},
            output=output,
            retry_count=0,
            token_count=7,
            last_error=None,
            display_name="Provider Planner",
            registration=registration,
        )

        artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-3",
            action_step=action_step,
            name="provider_plan",
            display_name="Provider Planner",
            registration=registration,
        )

        self.assertEqual(
            artifacts["trace"]["step"]["meta"]["tool"]["output_preview"],
            {
                "plan": "Analyze request -> Synthesize final answer",
                "steps": [
                    "Analyze request",
                    "Synthesize final answer",
                ],
            },
        )
        self.assertEqual(
            artifacts["observation"],
            "Provider Planner: Planned steps - Analyze request -> Synthesize final answer.",
        )
        self.assertEqual(
            artifacts["output"],
            {
                "plan": "Analyze request -> Synthesize final answer",
                "steps": [
                    "Analyze request",
                    "Synthesize final answer",
                ],
            },
        )

    def test_build_tool_iteration_success_artifacts_infer_preview_shape_for_extra_provider_planner_kind_with_tuple_steps(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="provider_plan",
            kind="provider_planner",
            label="Provider Planner",
            retryable_by_default=False,
            default_timeout_ms=8_000,
            requires_user_context=False,
            supports_result_preview=True,
            runner=lambda *, tool_input, prompt, user_id: {
                "tool_input": tool_input,
                "prompt": prompt,
                "user_id": user_id,
            },
        )
        output = {
            "plan": "Analyze request -> Synthesize final answer",
            "steps": (
                "Analyze request",
                "Synthesize final answer",
            ),
            "tool_kind": "provider_planner",
            "raw_payload": {"audit": "keep-raw-only"},
        }
        action_step = build_tool_step_success_update(
            action_step={
                "id": "step-3",
                "seq": 5,
                "type": "action",
                "content": "Tool running: Provider Planner",
                "meta": {
                    "tool": {
                        "name": "provider_plan",
                        "label": "Provider Planner",
                        "status": "running",
                    }
                },
            },
            name="provider_plan",
            tool_input={"prompt_preview": "please plan"},
            output=output,
            retry_count=0,
            token_count=7,
            last_error=None,
            display_name="Provider Planner",
            registration=registration,
        )

        artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-3",
            action_step=action_step,
            name="provider_plan",
            display_name="Provider Planner",
            registration=registration,
        )

        self.assertEqual(
            artifacts["trace"]["step"]["meta"]["tool"]["output_preview"],
            {
                "plan": "Analyze request -> Synthesize final answer",
                "steps": [
                    "Analyze request",
                    "Synthesize final answer",
                ],
            },
        )
        self.assertEqual(
            artifacts["observation"],
            "Provider Planner: Planned steps - Analyze request -> Synthesize final answer.",
        )
        self.assertEqual(
            artifacts["output"],
            {
                "plan": "Analyze request -> Synthesize final answer",
                "steps": [
                    "Analyze request",
                    "Synthesize final answer",
                ],
            },
        )

    def test_build_tool_iteration_success_artifacts_reuses_step_meta_summary_for_hot_retrieval_without_registry_context(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="task_retrieve_hot",
            kind="hot_knowledge_retrieval",
            label="Hot Retrieval",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            result_preview_keys=("tool_kind", "hit_count", "knowledge_base_id"),
            runner=lambda *, tool_input, prompt, user_id: {
                "tool_input": tool_input,
                "prompt": prompt,
                "user_id": user_id,
            },
        )
        output = {
            "tool_kind": "hot_knowledge_retrieval",
            "hit_count": 2,
            "knowledge_base_id": "demo-kb",
            "chunks": ["alpha", "beta"],
            "raw_documents": [{"id": "doc-1"}],
        }
        action_step = build_tool_step_success_update(
            action_step={
                "id": "step-2",
                "seq": 4,
                "type": "action",
                "content": "Tool running: Hot Retrieval",
                "meta": {
                    "tool": {
                        "name": "task_retrieve_hot",
                        "label": "Hot Retrieval",
                        "status": "running",
                    }
                },
            },
            name="task_retrieve_hot",
            tool_input={"query": "hot"},
            output=output,
            retry_count=0,
            token_count=7,
            last_error=None,
            display_name="Hot Retrieval",
            registration=registration,
        )

        artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-2",
            action_step=action_step,
            name="task_retrieve_hot",
            display_name="Hot Retrieval",
        )

        self.assertEqual(
            artifacts["output"],
            {
                "tool_kind": "hot_knowledge_retrieval",
                "hit_count": 2,
                "knowledge_base_id": "demo-kb",
            },
        )
        self.assertEqual(
            artifacts["trace"]["step"]["meta"]["tool"]["output_preview"],
            {
                "tool_kind": "hot_knowledge_retrieval",
                "hit_count": 2,
                "knowledge_base_id": "demo-kb",
            },
        )
        self.assertEqual(
            artifacts["observation"],
            "Hot Retrieval: Retrieved 2 hits from knowledge base demo-kb.",
        )

    def test_build_tool_iteration_success_artifacts_reuses_step_meta_preview_without_registry_context(
        self,
    ) -> None:
        registration = ToolRegistration(
            name="custom_lookup",
            kind="custom_lookup",
            label="Custom Lookup",
            retryable_by_default=False,
            default_timeout_ms=12_000,
            requires_user_context=False,
            supports_result_preview=True,
            result_preview_keys=("tool_kind", "hit_count"),
            runner=lambda *, tool_input, prompt, user_id: {
                "tool_input": tool_input,
                "prompt": prompt,
                "user_id": user_id,
            },
        )
        action_step = build_tool_step_success_update(
            action_step={
                "id": "step-4",
                "seq": 6,
                "type": "action",
                "content": "Tool running: Custom Lookup",
                "meta": {
                    "tool": {
                        "name": "custom_lookup",
                        "label": "Custom Lookup",
                        "status": "running",
                    }
                },
            },
            name="custom_lookup",
            tool_input={"query": "secret"},
            output={
                "tool_kind": "custom_lookup",
                "hit_count": 1,
                "secret": "do-not-preview",
            },
            retry_count=0,
            token_count=7,
            last_error=None,
            display_name="Custom Lookup",
            registration=registration,
        )

        artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-4",
            action_step=action_step,
            name="custom_lookup",
        )

        self.assertEqual(
            artifacts["observation"],
            'Custom Lookup: {"tool_kind": "custom_lookup", "hit_count": 1}',
        )
        self.assertEqual(
            artifacts["output"],
            {
                "tool_kind": "custom_lookup",
                "hit_count": 1,
                "secret": "do-not-preview",
            },
        )

    def test_build_tool_iteration_success_artifacts_accepts_tuple_effective_result_output_keys_from_step_meta(
        self,
    ) -> None:
        action_step = {
            "id": "step-5",
            "seq": 7,
            "type": "action",
            "content": "Tool done: Custom Lookup",
            "meta": {
                "tool": {
                    "name": "custom_lookup",
                    "label": "Custom Lookup",
                    "status": "done",
                    "effective_result_output_keys": (
                        "tool_kind",
                        "hit_count",
                    ),
                    "output": {
                        "tool_kind": "custom_lookup",
                        "hit_count": 1,
                        "secret": "do-not-preview",
                    },
                }
            },
        }

        artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-5",
            action_step=action_step,
            name="custom_lookup",
        )

        self.assertEqual(
            artifacts["observation"],
            'Custom Lookup: {"tool_kind": "custom_lookup", "hit_count": 1}',
        )
        self.assertEqual(
            artifacts["output"],
            {
                "tool_kind": "custom_lookup",
                "hit_count": 1,
                "secret": "do-not-preview",
            },
        )

    def test_build_tool_iteration_success_artifacts_reuses_step_meta_preview_as_output_without_raw_output(
        self,
    ) -> None:
        action_step = {
            "id": "step-6",
            "seq": 8,
            "type": "action",
            "content": "Tool done: Custom Lookup",
            "meta": {
                "tool": {
                    "name": "custom_lookup",
                    "label": "Custom Lookup",
                    "status": "done",
                    "output_preview": {
                        "tool_kind": "custom_lookup",
                        "hit_count": 1,
                    },
                }
            },
        }

        artifacts = build_tool_iteration_success_artifacts(
            task_id="task-1",
            step_id="step-6",
            action_step=action_step,
            name="custom_lookup",
        )

        self.assertEqual(
            artifacts["observation"],
            'Custom Lookup: {"tool_kind": "custom_lookup", "hit_count": 1}',
        )
        self.assertEqual(
            artifacts["output"],
            {
                "tool_kind": "custom_lookup",
                "hit_count": 1,
            },
        )
