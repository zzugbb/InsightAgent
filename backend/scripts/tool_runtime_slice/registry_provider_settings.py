from __future__ import annotations

from .context import *


class RegistryProviderSettingsMixin:
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
