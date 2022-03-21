using System;

using Azure.Sdk.Tools.PipelineWitness.Queue;
using Azure.Security.KeyVault.Secrets;

using Microsoft.ApplicationInsights.Extensibility;
using Microsoft.Azure.Functions.Extensions.DependencyInjection;
using Microsoft.Extensions.Azure;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.TeamFoundation.Build.WebApi;
using Microsoft.TeamFoundation.Core.WebApi;
using Microsoft.VisualStudio.Services.Common;
using Microsoft.VisualStudio.Services.TestResults.WebApi;
using Microsoft.VisualStudio.Services.WebApi;

[assembly: FunctionsStartup(typeof(Startup))]

namespace Azure.Sdk.Tools.PipelineWitness.Queue
{
    using Azure.Sdk.Tools.PipelineWitness.Common;
    using Azure.Sdk.Tools.PipelineWitness.Queue.ApplicationInsights;
    using Azure.Sdk.Tools.PipelineWitness.Queue.AzureDevOpsExport;

    public class Startup : FunctionsStartup
    {
        private string GetWebsiteResourceGroupEnvironmentVariable()
        {
            var websiteResourceGroupEnvironmentVariable = Environment.GetEnvironmentVariable("WEBSITE_RESOURCE_GROUP");
            return websiteResourceGroupEnvironmentVariable;
        }

        private string GetBuildBlobStorageEnvironmentVariable()
        {
            var environmentVariable = Environment.GetEnvironmentVariable("BUILD_BLOB_STORAGE_URI");
            return environmentVariable;
        }

        public override void Configure(IFunctionsHostBuilder builder)
        {
            var websiteResourceGroupEnvironmentVariable = GetWebsiteResourceGroupEnvironmentVariable();
            var buildBlobStorageUri = GetBuildBlobStorageEnvironmentVariable();

            builder.Services.AddAzureClients(builder =>
            {
                var keyVaultUri = new Uri($"https://{websiteResourceGroupEnvironmentVariable}.vault.azure.net/");
                builder.AddSecretClient(keyVaultUri);

                builder.AddBlobServiceClient(new Uri(buildBlobStorageUri));
            });

            builder.Services.AddSingleton<VssConnection>(provider =>
            {
                var secretClient = provider.GetService<SecretClient>();
                KeyVaultSecret secret = secretClient.GetSecret("azure-devops-personal-access-token");
                var credential = new VssBasicCredential("nobody", secret.Value);
                var connection = new VssConnection(new Uri("https://dev.azure.com/azure-sdk"), credential);
                return connection;
            });

            builder.Services.AddSingleton(provider => provider.GetRequiredService<VssConnection>().GetClient<ProjectHttpClient>());
            builder.Services.AddSingleton(provider => provider.GetRequiredService<VssConnection>().GetClient<BuildHttpClient>());
            builder.Services.AddSingleton(provider => provider.GetRequiredService<VssConnection>().GetClient<TestResultsHttpClient>());

            builder.Services.AddLogging();
            builder.Services.AddMemoryCache();
            builder.Services.AddSingleton<RunProcessor>();
            builder.Services.AddSingleton<PipelineRunProcessor>();
            builder.Services.AddSingleton<BuildLogProvider>();
            builder.Services.AddTransient<ITelemetryInitializer, NotFoundTelemetryInitializer>();
        }
    }
}
