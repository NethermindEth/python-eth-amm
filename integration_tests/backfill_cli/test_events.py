from decimal import Decimal

from click.testing import CliRunner
from eth_utils import to_checksum_address
from sqlalchemy import select

from python_eth_amm.cli.entry_point import cli_entry_point
from python_eth_amm.database.models.uniswap import (
    UniV3BurnEvent,
    UniV3CollectEvent,
    UniV3MintEvent,
)
from tests.resources.ABI import UNISWAP_V3_POOL_JSON

from .utils import printout_error_and_traceback


def test_backfill_mint_events_for_weth_wbtc_pool(
    integration_postgres_db,
    integration_db_session,
    cli_db_url,
    eth_rpc_cli_config,
    create_debug_logger,
):
    runner = CliRunner()
    migrate_res = runner.invoke(cli_entry_point, ["migrate-up", *cli_db_url])
    assert migrate_res.exit_code == 0

    with runner.isolated_filesystem():
        with open("UniswapV3Pool.json", "w") as f:
            f.write(UNISWAP_V3_POOL_JSON)

        result = runner.invoke(
            cli_entry_point,
            ["add-abi", "UniswapV3Pool", "UniswapV3Pool.json", *cli_db_url],
        )

        assert result.exit_code == 0

    mint_backfill_result = runner.invoke(
        cli_entry_point,
        [
            "backfill",
            "events",
            "-from",
            17_800_000,
            "-to",
            17_900_000,
            "--contract-address",
            to_checksum_address("0xcbcdf9626bc03e24f779434178a73a0b4bad62ed"),
            "-abi",
            "UniswapV3Pool",
            "--event-name",
            "Mint",
            *cli_db_url,
            *eth_rpc_cli_config,
        ],
        input="y",
    )

    printout_error_and_traceback(mint_backfill_result)

    assert mint_backfill_result.exit_code == 0

    expected_output = [
        "------ Backfill Plan for Ethereum Events ------",
        "Backfill Block Ranges",
        "17,800,000",
        "17,900,000",
        "100,000",
        "0xCBCdF9626bC03E24f779434178A73a0B4bad62eD",
        "UniswapV3Pool ABI Decoding Events:",
        "'Mint'",
    ]

    for line in expected_output:
        assert line in mint_backfill_result.output

    mint_events = integration_db_session.execute(select(UniV3MintEvent)).scalars().all()
    assert mint_events[0].sender == bytes.fromhex(
        "C36442b4a4522E871399CD717aBDD847Ab11FE88"
    )

    assert mint_events[0].amount == 32500065523907
    assert mint_events[0].tick_lower == 254220
    assert mint_events[0].tick_upper == 258060

    assert mint_events[-1].amount == 5108528917685
    assert mint_events[-1].tick_lower == 255480
    assert mint_events[-1].tick_upper == 258900

    assert len(mint_events) == 95


def test_cli_backfill_multiple_events(
    integration_postgres_db,
    integration_db_session,
    cli_db_url,
    eth_rpc_cli_config,
    create_debug_logger,
):
    runner = CliRunner()
    runner.invoke(cli_entry_point, ["migrate-up", *cli_db_url])

    with runner.isolated_filesystem():
        with open("UniswapV3Pool.json", "w") as f:
            f.write(UNISWAP_V3_POOL_JSON)

        result = runner.invoke(
            cli_entry_point,
            ["add-abi", "UniswapV3Pool", "UniswapV3Pool.json", *cli_db_url],
        )

        assert result.exit_code == 0

    event_backfill_res = runner.invoke(
        cli_entry_point,
        [
            "backfill",
            "events",
            "-from",
            18_000_000,
            "-to",
            18_005_000,
            "--contract-address",
            to_checksum_address("0xcbcdf9626bc03e24f779434178a73a0b4bad62ed"),
            "-abi",
            "UniswapV3Pool",
            "--event-name",
            "Mint",
            "--event-name",
            "Burn",
            "--event-name",
            "Collect",
            *cli_db_url,
            *eth_rpc_cli_config,
        ],
        input="y",
    )

    expected_out = [
        "18,000,000",
        "18,005,000",
        "UniswapV3Pool ABI Decoding Events:",
        "'Mint', 'Burn', 'Collect'",
    ]

    for out in expected_out:
        assert out in event_backfill_res.output

    mint_events = integration_db_session.execute(select(UniV3MintEvent)).scalars().all()
    burn_events = integration_db_session.execute(select(UniV3BurnEvent)).scalars().all()
    collect_events = (
        integration_db_session.execute(select(UniV3CollectEvent)).scalars().all()
    )

    assert event_backfill_res.exit_code == 0

    assert len(mint_events) == 6
    assert len(burn_events) == 7
    assert len(collect_events) == 8

    assert mint_events[0].tick_lower == 250920
    assert mint_events[0].tick_upper == 264780

    assert mint_events[-1].tick_lower == 251280
    assert mint_events[-1].tick_upper == 264360

    assert burn_events[0].tick_lower == 255960
    assert burn_events[0].tick_upper == 258300

    assert burn_events[-1].tick_lower == collect_events[-1].tick_lower == 251280
    assert burn_events[-1].tick_upper == collect_events[-1].tick_upper == 264360

    assert burn_events[-1].amount_0 == collect_events[-1].amount_0 == Decimal("398206")
    assert (
        burn_events[-1].amount_1
        == collect_events[-1].amount_1
        == Decimal("63404179018897713")
    )


def test_event_cli_required_params(
    integration_postgres_db, integration_db_session, cli_db_url
):
    runner = CliRunner()

    runner.invoke(cli_entry_point, ["migrate-up", *cli_db_url])

    missing_contract_address = runner.invoke(
        cli_entry_point,
        [
            "backfill",
            "events",
            "-abi",
            "UniswapV3Pool",
            "--event-name",
            "Mint",
            *cli_db_url,
        ],
    )

    missing_abi_name = runner.invoke(
        cli_entry_point,
        [
            "backfill",
            "events",
            "--contract-address",
            to_checksum_address("0xcbcdf9626bc03e24f779434178a73a0b4bad62ed"),
            "--event-name",
            "Mint",
            *cli_db_url,
        ],
    )

    invalid_abi = runner.invoke(
        cli_entry_point,
        [
            "backfill",
            "events",
            "--contract-address",
            to_checksum_address("0xcbcdf9626bc03e24f779434178a73a0b4bad62ed"),
            "-abi",
            "InvalidABI",
            "--event-name",
            "Mint",
            *cli_db_url,
        ],
    )

    assert missing_contract_address.exit_code == 2
    assert (
        "Error: Missing option '--contract-address'" in missing_contract_address.output
    )

    assert missing_abi_name.exit_code == 0
    assert (
        "Error Occurred Generating Backfill: Expected 1 ABI for Event backfill"
        in missing_abi_name.output
    )
    assert "Specify an ABI using --contract-abi" in missing_abi_name.output

    assert invalid_abi.exit_code == 0

    expected_error = [
        "Error Occurred Generating Backfill:",
        "ABIs not in DB: InvalidABI",
    ]
    for line in expected_error:
        assert line in invalid_abi.output