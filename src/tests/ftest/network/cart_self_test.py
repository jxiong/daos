"""
  (C) Copyright 2018-2024 Intel Corporation.
  (C) Copyright 2025 Hewlett Packard Enterprise Development LP

  SPDX-License-Identifier: BSD-2-Clause-Patent
"""
from apricot import TestWithServers
from command_utils import ExecutableCommand
from command_utils_base import EnvironmentVariables, FormattedParameter
from exception_utils import CommandFailure
from host_utils import get_local_host
from job_manager_utils import get_job_manager


class CartSelfTest(TestWithServers):
    """Runs a few variations of CaRT self-test.

    Ensures network is in a stable state prior to testing.

    :avocado: recursive
    """

    class SelfTest(ExecutableCommand):
        """Defines a CaRT self test command."""

        def __init__(self, path=""):
            """Create a SelfTest object.

            Uses Avocado's utils.process module to run self_test with
            parameters.

            Args:
                path (str, optional): path to location of command binary file.
                    Defaults to "".
            """
            super().__init__("/run/self_test/*", "self_test", path)

            self.group_name = FormattedParameter("--group-name {}")
            self.endpoint = FormattedParameter("--endpoint {0}")
            self.message_sizes = FormattedParameter("--message-sizes {0}")

            max_rpc_opt = "--max-inflight-rpcs {0}"
            self.max_inflight_rpcs = FormattedParameter(max_rpc_opt)

            self.repetitions = FormattedParameter("--repetitions {0}")
            self.use_daos_agent_env = FormattedParameter(
                "--use-daos-agent-env", True)

    def __init__(self, *args, **kwargs):
        """Initialize a CartSelfTest object."""
        super().__init__(*args, **kwargs)
        self.uri_file = None
        self.cart_env = EnvironmentVariables()

    def setUp(self):
        """Set up each test case."""
        super().setUp()

        # Configure the daos server
        self.add_server_manager()
        self.configure_manager(
            "server",
            self.server_managers[-1],
            self.hostlist_servers,
            self.hostfile_servers_slots,
            self.mgmt_svc_replicas)

        # Setup additional environment variables for the server orterun command
        self.cart_env["CRT_CTX_NUM"] = "8"
        self.cart_env["D_PROVIDER"] = \
            self.server_managers[0].get_config_value("provider")
        self.cart_env["D_INTERFACE"] = \
            self.server_managers[0].get_config_value("fabric_iface")
        self.cart_env["DAOS_AGENT_DRPC_DIR"] = "/var/run/daos_agent/"

        self.server_managers[0].manager.assign_environment(self.cart_env, True)
        self.server_managers[0].detect_start_via_dmg = True

        # Start the daos server
        self.start_server_managers()
        self.register_cleanup(self.stop_servers)

    def test_self_test(self):
        """Run a few CaRT self-test scenarios.

        :avocado: tags=all,pr,daily_regression
        :avocado: tags=vm
        :avocado: tags=network,smoke,cart
        :avocado: tags=CartSelfTest,unittest,test_self_test
        """
        # Setup the orterun command
        orterun = get_job_manager(self, "Orterun", self.SelfTest(self.bin), mpi_type="openmpi")
        orterun.assign_hosts(get_local_host(), hostfile=False)
        orterun.map_by.update(None, "orterun/map_by")
        orterun.enable_recovery.update(False, "orterun/enable_recovery")

        # Get the self_test command line parameters
        orterun.job.get_params(self)
        orterun.job.group_name.update(self.server_group, "group_name")

        # Setup the environment variables for the self_test orterun command
        orterun.assign_environment(self.cart_env)

        # Run the test
        try:
            orterun.run()
        except CommandFailure as error:
            self.log.info(
                "CaRT self_test returned non-zero: %s", str(error))
            self.fail("CaRT self_test returned non-zero")
