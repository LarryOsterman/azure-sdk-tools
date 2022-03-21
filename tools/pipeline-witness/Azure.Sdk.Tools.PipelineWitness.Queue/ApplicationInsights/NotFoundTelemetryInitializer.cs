using System;

using Microsoft.ApplicationInsights.Channel;
using Microsoft.ApplicationInsights.DataContracts;
using Microsoft.ApplicationInsights.Extensibility;

namespace Azure.Sdk.Tools.PipelineWitness.Queue.ApplicationInsights
{
    public class NotFoundTelemetryInitializer : ITelemetryInitializer
    {
        public NotFoundTelemetryInitializer()
        {

        }

        public void Initialize(ITelemetry telemetry)
        {
            // Is this a TrackRequest() ?
            if (!(telemetry is DependencyTelemetry dependencyTelemetry))
            {
                return;
            }

            if (dependencyTelemetry.Success != false)
            {
                // we only care to fix false failures
                return;
            }

            if(!int.TryParse(dependencyTelemetry.ResultCode, out var code) || (code != 404 && code != 409))
            {
                // We only care about 404 NotFound and 409 Conflict response codes
                return;
            }

            // Set failed dependency call to success
            dependencyTelemetry.Success = true;
        }
    }
}
