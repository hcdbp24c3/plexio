import { z } from 'zod';

const sectionSchema = z.object({
  key: z.string(),
  title: z.string(),
  type: z.string(),
});

const serverConfigSchema = z.object({
  serverName: z.string(),
  discoveryUrl: z.string(),
  streamingUrl: z.string(),
  sections: z.array(sectionSchema),
});

export const formSchema = z.object({
  selectedServers: z.array(z.string()).min(1, 'Select at least one server'),
  serverConfigs: z.array(serverConfigSchema),
  includeTranscodeOriginal: z.boolean(),
  includeTranscodeDown: z.boolean(),
  transcodeDownQualities: z.array(z.string()).optional(),
  includeCatalogs: z.boolean(),
  includePlexTv: z.boolean(),
});

export type ConfigurationFormType = z.infer<typeof formSchema>;
export type ServerConfigType = z.infer<typeof serverConfigSchema>;
