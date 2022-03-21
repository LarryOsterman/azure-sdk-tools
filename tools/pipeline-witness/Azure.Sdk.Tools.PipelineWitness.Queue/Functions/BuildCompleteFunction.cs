using System;
using System.Threading.Tasks;

using Azure.Storage.Queues.Models;

using Microsoft.Azure.WebJobs;
using Microsoft.Extensions.Logging;
using Newtonsoft.Json.Linq;

namespace Azure.Sdk.Tools.PipelineWitness.Queue.Functions
{
    public class BuildCompleteFunction
    {
        public BuildCompleteFunction(ILogger<BuildCompleteFunction> logger, RunProcessor runProcessor)
        {
            this.logger = logger;
            this.runProcessor = runProcessor;
        }

        private ILogger logger;
        private RunProcessor runProcessor;

        [FunctionName("BuildComplete")]
        public async Task Run([QueueTrigger("ado-build-completed")]QueueMessage message)
        {
            logger.LogInformation("Processing build.complete event.");
            var messageBody = message.MessageText;
            logger.LogInformation("Message body was: {messageBody}", messageBody);

            logger.LogInformation("Extracting content from message.");

            var devopsEvent = JObject.Parse(messageBody);

            var buildId = devopsEvent["resource"]?.Value<int>("id");

            if (buildId == null)
            {
                this.logger.LogError("Message contained no build id. Message body: {MessageBody}", messageBody);
                return;
            }

            var projectId = devopsEvent["resourceContainers"]?["project"]?.Value<string>("id");

            if (projectId == null)
            {
                this.logger.LogError("Message contained no project id. Message body: {MessageBody}", messageBody);
                return;
            }

            if (!Guid.TryParse(projectId, out var projectGiud))
            {
                this.logger.LogError("Could not parse project id as a guid '{ProjectId}'", projectId);
                return;
            }

            await runProcessor.ProcessRunAsync(projectGiud, buildId.Value);
        }
    }
}
