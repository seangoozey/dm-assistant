param(
    [string[]]$TestPath = @("tests/test_claim_reconciliation_postgres.py")
)

$ErrorActionPreference = "Stop"
$testDatabase = "campaign_core_integration_test"
$databaseContainer = "dm-assistant-campaign-db-1"
$coreImage = "dm-assistant-campaign-core:0.1.0"
$testImage = "dm-assistant-campaign-core-test:0.1.0"
$databaseNetwork = "dm-assistant_campaign-database"
$repositoryFixtures = (Resolve-Path (Join-Path $PSScriptRoot "..\tests\fixtures")).Path

if (-not $testDatabase.EndsWith("_test")) {
    throw "Refusing to manage a database whose name does not end in _test"
}

docker inspect $databaseContainer | Out-Null
docker exec $databaseContainer dropdb --if-exists -U campaign_owner $testDatabase
docker exec $databaseContainer createdb -U campaign_owner $testDatabase

try {
    docker build --file campaign-core/Dockerfile.test --tag $testImage campaign-core
    if ($LASTEXITCODE -ne 0) {
        throw "Campaign Core test image build failed with exit code $LASTEXITCODE"
    }
    $dockerArguments = @(
        "run", "--rm",
        "--network", $databaseNetwork,
        "--volume", "${repositoryFixtures}:/tests/fixtures:ro",
        "--env", "CAMPAIGN_TEST_DATABASE_URL=postgresql://campaign_owner:campaignPassword@campaign-db:5432/$testDatabase",
        $testImage
    ) + $TestPath
    & docker $dockerArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Campaign Core PostgreSQL tests failed with exit code $LASTEXITCODE"
    }
}
finally {
    docker exec $databaseContainer dropdb --if-exists -U campaign_owner $testDatabase
}
