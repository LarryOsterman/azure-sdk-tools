namespace Azure.Sdk.Tools.PipelineWitness.Queue
{
    using System;
    using System.Threading.Tasks;

    using Azure.Sdk.Tools.PipelineWitness.Queue.AzureDevOpsExport;

    using Microsoft.TeamFoundation.Build.WebApi;
    using Microsoft.VisualStudio.Services.WebApi;

    public class RunProcessor
    {
        public RunProcessor(
            VssConnection vssConnection,
            PipelineRunProcessor pipelineRunProcessor)
        {
            this.pipelineRunProcessor = pipelineRunProcessor ?? throw new ArgumentNullException(nameof(pipelineRunProcessor));
            this.vssConnection = vssConnection ?? throw new ArgumentNullException(nameof(vssConnection));
        }

        private const string Account = "azure-sdk";
        private readonly VssConnection vssConnection;
        private readonly PipelineRunProcessor pipelineRunProcessor;

        public async Task ProcessRunAsync(Guid projectId, int buildId)
        {
            var buildClient = vssConnection.GetClient<BuildHttpClient>();

            var timeline = await buildClient.GetBuildTimelineAsync(projectId, buildId);
            var build = await buildClient.GetBuildAsync(projectId, buildId);

            await this.pipelineRunProcessor.UploadBuildBlobsAsync(Account, build, timeline);
        }
    }
}
