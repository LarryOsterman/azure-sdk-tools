// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

import { getClient, ClientOptions } from "@azure-rest/core-client";
import { logger } from "./logger.js";
import { TokenCredential } from "@azure/core-auth";
import { WidgetManagerClient } from "./clientDefinitions.js";

/** The optional parameters for the client */
export interface WidgetManagerClientOptions extends ClientOptions {
  /** The api version option of the client */
  apiVersion?: string;
}

/**
 * Initialize a new instance of `WidgetManagerClient`
 * @param endpointParam - The parameter endpointParam
 * @param credentials - uniquely identify client credential
 * @param options - the parameter for all optional parameters
 */
export default function createClient(
  endpointParam: string,
  credentials: TokenCredential,
  {
    apiVersion = "2022-11-01-preview",
    ...options
  }: WidgetManagerClientOptions = {},
): WidgetManagerClient {
  const endpointUrl = options.endpoint ?? options.baseUrl ?? `${endpointParam}`;
  const userAgentInfo = `azsdk-js-contoso-widgetmanager-rest/1.0.0-beta.1`;
  const userAgentPrefix =
    options.userAgentOptions && options.userAgentOptions.userAgentPrefix
      ? `${options.userAgentOptions.userAgentPrefix} ${userAgentInfo}`
      : `${userAgentInfo}`;
  options = {
    ...options,
    userAgentOptions: {
      userAgentPrefix,
    },
    loggingOptions: {
      logger: options.loggingOptions?.logger ?? logger.info,
    },
    credentials: {
      scopes: options.credentials?.scopes ?? [
        "https://contoso.azure.com/.default",
      ],
    },
  };
  const client = getClient(
    endpointUrl,
    credentials,
    options,
  ) as WidgetManagerClient;

  client.pipeline.removePolicy({ name: "ApiVersionPolicy" });
  client.pipeline.addPolicy({
    name: "ClientApiVersionPolicy",
    sendRequest: (req, next) => {
      // Use the apiVersion defined in request url directly
      // Append one if there is no apiVersion and we have one at client options
      const url = new URL(req.url);
      if (!url.searchParams.get("api-version") && apiVersion) {
        req.url = `${req.url}${
          Array.from(url.searchParams.keys()).length > 0 ? "&" : "?"
        }api-version=${apiVersion}`;
      }

      return next(req);
    },
  });

  return client;
}
