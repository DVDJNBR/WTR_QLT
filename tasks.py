
"""
🌊 Water Quality Pipeline - Infrastructure Management
Inspired by the old Lake manager but simplified with invoke
"""

import os
import subprocess
from pathlib import Path
from invoke import task
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich import print as rprint
from loguru import logger

# Configuration
TERRAFORM_DIR = Path(".cloud")
ROOT_DIR = Path(".")
console = Console()

# Configure loguru
logger.remove()
logger.add(
    "logs/infrastructure.log",
    rotation="10 MB",
    retention="30 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)
logger.add(lambda msg: None, level="INFO")  # Disable console output for loguru
console = Console()

# Configure loguru
logger.remove()
logger.add("logs/water_quality_{time}.log", rotation="1 day", retention="7 days")
logger.add(lambda msg: None, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")

def run_terraform_command(command: str, cwd: Path = TERRAFORM_DIR):
    """Execute terraform command in the specified directory"""
    console.print(f"Running: [cyan]{command}[/cyan]")
    console.print(f"Directory: [dim]{cwd}[/dim]")
    logger.info(f"Executing terraform command: {command} in {cwd}")
    
    # Load .env file for terraform
    env = os.environ.copy()
    env_file = ROOT_DIR / ".env"
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    env[key] = value
    
    result = subprocess.run(
        command,
        shell=True,
        cwd=cwd,
        capture_output=False,
        env=env
    )
    
    if result.returncode != 0:
        console.print(f"[red]Command failed: {command}[/red]")
        logger.error(f"Terraform command failed: {command}")
        raise Exception(f"Command failed: {command}")
    
    logger.info(f"Terraform command completed successfully: {command}")
    return result.returncode

@task(name="get-subscription")
def setup_env(c):
    """Get Azure subscription ID and save to .env"""
    console.print("Setting up environment file...", style="blue")
    logger.info("Starting environment setup")
    
    env_file = ROOT_DIR / ".env"
    
    # Get current Azure subscription ID
    try:
        result = subprocess.run(
            "az account show --query id -o tsv",
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            console.print("Failed to get Azure subscription ID", style="red")
            console.print("Make sure you're logged in with: [cyan]az login[/cyan]", style="yellow")
            logger.error("Failed to retrieve Azure subscription ID")
            return
        
        subscription_id = result.stdout.strip()
        console.print(f"Found subscription: [green]{subscription_id}[/green]")
        logger.info(f"Retrieved subscription ID: {subscription_id}")
        
        # Create or update .env file
        env_content = f"# Azure Configuration\nTF_VAR_subscription_id={subscription_id}\nAZURE_SUBSCRIPTION_ID={subscription_id}\n\n"
        
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        console.print("Environment file created successfully", style="green")
        logger.info("Environment file created with subscription ID")
        
    except Exception as e:
        console.print(f"Error setting up environment: {e}", style="red")
        logger.error(f"Environment setup failed: {e}")

@task(name="tf-init")
def init(c):
    """Initialize Terraform infrastructure"""
    console.print("Initializing Terraform...", style="blue")
    run_terraform_command("terraform init")
    console.print("Terraform initialized", style="green")

@task(name="tf-plan")
def plan(c):
    """Create Terraform execution plan for water quality pipeline"""
    console.print("Creating Terraform plan...", style="blue")
    run_terraform_command("terraform plan -out=tfplan")
    console.print("Plan created", style="green")

@task(name="tf-apply")
def apply(c):
    """Deploy water quality pipeline infrastructure to Azure"""
    console.print("Applying Terraform configuration...", style="blue")
    run_terraform_command("terraform apply tfplan")
    console.print("Infrastructure deployed", style="green")
    
    # Auto-save environment variables after successful deployment
    save_env(c)

@task(name="azure-destroy")
def destroy(c):
    """DESTROY ALL Azure water quality pipeline resources (Data Lake + Databricks)"""
    console.print("This will PERMANENTLY DELETE:", style="red bold")
    console.print("  - Data Lake Storage (wtrqltadls)", style="red")
    console.print("  - Databricks Workspace (wtr-qlt-dbw-v2)", style="red")
    console.print("  - All data in bronze/silver/gold containers", style="red")
    console.print("  - Resource Group: RG_DBREAU", style="red")
    
    confirm = input("\nType 'DESTROY' to confirm total destruction: ")
    if confirm != 'DESTROY':
        console.print("Operation cancelled - infrastructure preserved", style="yellow")
        return
    
    console.print("Destroying ALL water quality pipeline resources...", style="red")
    run_terraform_command("terraform destroy -auto-approve")
    console.print("All Azure resources destroyed", style="green")

@task(name="tf-output")
def output(c):
    """Show deployed infrastructure details (URLs, names, etc.)"""
    console.print("Terraform outputs:", style="blue")
    run_terraform_command("terraform output")

@task(name="azure-deploy")
def deploy(c):
    """Deploy complete water quality pipeline (Data Lake + Databricks)"""
    console.print("Starting full deployment...", style="blue")
    init(c)
    plan(c)
    apply(c)  # apply() calls save_env() automatically
    console.print("Deployment completed", style="green")

@task(name="env-save")
def save_env(c):
    """💾 Save infrastructure URLs and names to .env file"""
    console = Console()
    console.print("💾 Saving Terraform outputs to .env file...", style="blue")
    
    env_file = ROOT_DIR / ".env"
    
    # Get subscription ID
    try:
        result = subprocess.run("az account show --query id -o tsv", shell=True, capture_output=True, text=True)
        subscription_id = result.stdout.strip() if result.returncode == 0 else "your-subscription-id"
    except:
        subscription_id = "your-subscription-id"
    
    # Get Terraform outputs
    original_dir = os.getcwd()
    os.chdir(TERRAFORM_DIR)
    
    outputs = {}
    try:
        # Get each output
        output_commands = {
            "DATALAKE_NAME": "terraform output -raw datalake_name",
            "DATALAKE_ACCESS_KEY": "terraform output -raw datalake_primary_access_key", 
            "DATALAKE_CONNECTION_STRING": "terraform output -raw datalake_connection_string",
            "DATABRICKS_WORKSPACE_URL": "terraform output -raw databricks_workspace_url",
            "RESOURCE_GROUP_NAME": "terraform output -raw resource_group_name"
        }
        
        for key, cmd in output_commands.items():
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                outputs[key] = result.stdout.strip()
            else:
                console.print(f"⚠️  Could not get {key}", style="yellow")
                outputs[key] = f"error-getting-{key.lower()}"
    
    finally:
        os.chdir(original_dir)
    
    # Write .env file
    env_content = f"""# ===================================================================
# 🌊 Water Quality Pipeline - Environment Variables
# ===================================================================

# 🔐 AZURE CREDENTIALS
AZURE_SUBSCRIPTION_ID={subscription_id}

# 🌊 DATA LAKE STORAGE
DATALAKE_NAME={outputs.get('DATALAKE_NAME', 'not-found')}
DATALAKE_ACCESS_KEY={outputs.get('DATALAKE_ACCESS_KEY', 'not-found')}
DATALAKE_CONNECTION_STRING={outputs.get('DATALAKE_CONNECTION_STRING', 'not-found')}

# 🧱 DATABRICKS WORKSPACE
DATABRICKS_WORKSPACE_URL={outputs.get('DATABRICKS_WORKSPACE_URL', 'not-found')}

# 📦 AZURE RESOURCES
RESOURCE_GROUP_NAME={outputs.get('RESOURCE_GROUP_NAME', 'not-found')}
"""
    
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    console.print(f"✅ Environment variables saved to {env_file}", style="green")
    console.print("📋 Contents:", style="cyan")
    console.print(env_content)

@task(name="infra-status")
def status(c):
    """📊 Check water quality pipeline infrastructure status"""
    print("📊 Infrastructure Status:")
    print("=" * 50)
    
    # Check if terraform is initialized
    if (TERRAFORM_DIR / ".terraform").exists():
        print("✅ Terraform initialized")
    else:
        print("❌ Terraform not initialized")
    
    # Check if plan exists
    if (TERRAFORM_DIR / "tfplan").exists():
        print("✅ Terraform plan exists")
    else:
        print("❌ No terraform plan found")
    
    # Check if .env exists
    if (ROOT_DIR / ".env").exists():
        print("✅ .env file exists")
    else:
        print("❌ No .env file found")
    
    print("=" * 50)

@task(name="tf-import")
def import_existing(c):
    """📥 Import existing Azure resources into Terraform state"""
    print("📥 Importing existing resources...")
    
    # Import existing Databricks workspace if it exists
    try:
        run_terraform_command(
            "terraform import azurerm_databricks_workspace.main "
            "/subscriptions/029b3537-0f24-400b-b624-6058a145efe1/resourceGroups/RG_DBREAU/providers/Microsoft.Databricks/workspaces/dbw-water-quality-france"
        )
        print("✅ Databricks workspace imported")
    except:
        print("⚠️  Databricks workspace not found or already imported")
    
    # Import storage account if it exists
    try:
        run_terraform_command(
            "terraform import azurerm_storage_account.datalake "
            "/subscriptions/029b3537-0f24-400b-b624-6058a145efe1/resourceGroups/RG_DBREAU/providers/Microsoft.Storage/storageAccounts/adls4waterquality"
        )
        print("✅ Storage account imported")
    except:
        print("⚠️  Storage account not found or already imported")

@task(name="tf-unlock")
def unlock(c, lock_id=None):
    """🔓 Force unlock Terraform state (use when locked)"""
    if not lock_id:
        print("❌ Please provide lock ID: invoke tf-unlock --lock-id=YOUR_LOCK_ID")
        return
    
    print(f"🔓 Force unlocking Terraform state: {lock_id}")
    run_terraform_command(f"terraform force-unlock -force {lock_id}")
    print("✅ State unlocked")

@task(name="clean-files")
def clean(c):
    """🧹 Clean local terraform files and .env (keeps Azure resources)"""
    print("🧹 Cleaning terraform files...")
    
    files_to_clean = [
        TERRAFORM_DIR / "tfplan",
        TERRAFORM_DIR / "terraform.tfstate",
        TERRAFORM_DIR / "terraform.tfstate.backup",
        TERRAFORM_DIR / ".terraform.lock.hcl",
        ROOT_DIR / ".env"
    ]
    
    for file_path in files_to_clean:
        if file_path.exists():
            file_path.unlink()
            print(f"🗑️  Removed: {file_path}")
    
    print("✅ Cleanup completed")

@task(name="databricks-config")
def configure_databricks(c):
    """🔧 Configure Databricks for cost optimization"""
    console = Console()
    
    # Get Databricks workspace URL from .env
    env_file = ROOT_DIR / ".env"
    workspace_url = None
    
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith('DATABRICKS_WORKSPACE_URL='):
                    workspace_url = line.split('=', 1)[1].strip()
                    break
    
    if not workspace_url:
        console.print("❌ Databricks workspace URL not found in .env", style="red")
        console.print("Run 'invoke env-save' first!", style="yellow")
        return
    
    console.print(f"🔧 Configuring Databricks workspace: {workspace_url}", style="blue")
    
    # Create cluster policy for cost optimization
    cluster_policy = {
        "name": "Water Quality - Cost Optimized",
        "definition": {
            "cluster_type": {"type": "fixed", "value": "all-purpose"},
            "autotermination_minutes": {"type": "fixed", "value": 120},
            "num_workers": {"type": "range", "min": 0, "max": 4},
            "node_type_id": {"type": "allowlist", "values": ["Standard_DS3_v2", "Standard_D4s_v3"]},
            "enable_elastic_disk": {"type": "fixed", "value": False},
            "runtime_engine": {"type": "fixed", "value": "STANDARD"}
        }
    }
    
    console.print("📋 Cluster policy created (cost-optimized)", style="green")
    console.print("💡 Next steps:", style="cyan")
    console.print("  1. Go to Databricks workspace", style="white")
    console.print("  2. Admin Console > Cluster Policies", style="white")
    console.print("  3. Apply 'Water Quality - Cost Optimized' policy", style="white")
    console.print("  4. Set auto-termination to 120 minutes", style="white")

@task(name="databricks-cluster")
def create_cluster(c):
    """🚀 Create cost-optimized cluster for water quality pipeline"""
    console = Console()
    
    cluster_config = {
        "cluster_name": "water-quality-cluster",
        "spark_version": "13.3.x-scala2.12",
        "node_type_id": "Standard_DS3_v2",
        "num_workers": 1,
        "autotermination_minutes": 120,
        "enable_elastic_disk": False,
        "cluster_source": "UI"
    }
    
    console.print("🚀 Cluster configuration ready:", style="blue")
    console.print(f"  Name: {cluster_config['cluster_name']}", style="white")
    console.print(f"  Runtime: {cluster_config['spark_version']}", style="white")
    console.print(f"  Workers: {cluster_config['num_workers']}", style="white")
    console.print(f"  Auto-stop: {cluster_config['autotermination_minutes']} min", style="white")
    
    console.print("\n💡 To create this cluster:", style="cyan")
    console.print("  1. Go to Databricks workspace", style="white")
    console.print("  2. Compute > Create Cluster", style="white")
    console.print("  3. Use the config above", style="white")

@task(name="pipeline-setup")
def full_setup(c):
    """🎯 Complete water quality pipeline setup (Azure + env files)"""
    print("🚀 Starting complete setup...")
    setup_env(c)
    deploy(c)  # deploy() calls save_env() automatically via apply()
    print("🎉 Setup completed! Check your .env file for credentials.")