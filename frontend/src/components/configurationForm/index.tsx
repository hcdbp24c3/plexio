import { FC } from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { encode as base64_encode } from 'js-base64';
import { useForm } from 'react-hook-form';
import { v4 as uuidv4 } from 'uuid';
import {
  IncludeCatalogsField,
  IncludeTranscodeOriginalField,
  IncludeTranscodeDownFields,
  IncludePlexTvField,
  ServerCheckboxListField,
  PerServerConfig,
} from '@/components/configurationForm/fields';
import {
  formSchema,
  ConfigurationFormType,
} from '@/components/configurationForm/formSchema.tsx';
import { Icons } from '@/components/icons';
import { Button } from '@/components/ui/button.tsx';
import { Form } from '@/components/ui/form';
import { PlexServer } from '@/types/plex.tsx';

interface Props {
  servers: PlexServer[];
}

const ConfigurationForm: FC<Props> = ({ servers }) => {
  const form = useForm<ConfigurationFormType>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      selectedServers: [],
      serverConfigs: [],
      includeCatalogs: true,
      includeTranscodeOriginal: false,
      includeTranscodeDown: false,
      includePlexTv: false,
    },
  });

  const selectedServerNames = form.watch('selectedServers');
  // Render in serverConfigs order — group index must match its form-field index.
  const serverConfigs = form.watch('serverConfigs');

  const handleSelectionChange = (selectedNames: string[]) => {
    const currentConfigs = form.getValues('serverConfigs');

    // Find configs to keep (servers still selected)
    const configsToKeep = selectedNames
      .map((name) => {
        const existing = currentConfigs.find((c) => c.serverName === name);
        if (existing) return existing;
        // New server selected — add default config
        return {
          serverName: name,
          discoveryUrl: '',
          streamingUrl: '',
          sections: [],
        };
      })
      .filter(Boolean);

    form.setValue('serverConfigs', configsToKeep);
  };

  function onSubmit(
    configuration: ConfigurationFormType,
    event?: React.BaseSyntheticEvent,
  ) {
    const payload = {
      servers: configuration.serverConfigs
        .filter((config) =>
          configuration.selectedServers.includes(config.serverName),
        )
        .map((config) => {
          const plexServer = servers.find(
            (s) => s.name === config.serverName,
          );
          return {
            accessToken: plexServer?.accessToken ?? '',
            discoveryUrl: config.discoveryUrl,
            streamingUrl: config.streamingUrl,
            serverName: config.serverName,
            sections: config.sections.map((s) => ({
              key: s.key,
              title: s.title,
              type: s.type,
            })),
          };
        }),
      includeCatalogs: configuration.includeCatalogs,
      includeTranscodeOriginal: configuration.includeTranscodeOriginal,
      includeTranscodeDown: configuration.includeTranscodeDown,
      transcodeDownQualities: configuration.transcodeDownQualities ?? [],
      includePlexTv: configuration.includePlexTv,
      version: __APP_VERSION__,
    };

    const encodedConfiguration = base64_encode(JSON.stringify(payload));
    const addonUrl = `${window.location.origin}/${uuidv4()}/${encodedConfiguration}/manifest.json`;

    const submitter = (event?.nativeEvent as SubmitEvent)?.submitter as
      | HTMLButtonElement
      | undefined;
    if (submitter?.name === 'clipboard') {
      void navigator.clipboard.writeText(addonUrl);
    } else {
      window.location.href = addonUrl.replace(/https?:\/\//, 'stremio://');
    }
  }

  return (
    <Form {...form}>
      <form
        // eslint-disable-next-line @typescript-eslint/no-misused-promises
        onSubmit={form.handleSubmit(onSubmit)}
        className="space-y-2 p-2 rounded-lg border"
      >
        <ServerCheckboxListField
          form={form}
          servers={servers}
          onSelectionChange={handleSelectionChange}
        />

        {serverConfigs.map((config, index) => {
          const server = servers.find((s) => s.name === config.serverName);
          if (!server) return null;
          return (
            <PerServerConfig
              key={server.name}
              form={form}
              server={server}
              index={index}
            />
          );
        })}

        <IncludeCatalogsField form={form} />
        <IncludeTranscodeOriginalField form={form} />
        <IncludeTranscodeDownFields form={form} />
        <IncludePlexTvField form={form} />

        <div className="flex items-center space-x-1 justify-center p-3">
          <Button
            className="h-11 w-10 p-2"
            type="submit"
            name="clipboard"
            disabled={selectedServerNames.length === 0}
          >
            <Icons.clipboard />
          </Button>
          <Button
            className="h-11 rounded-md px-8 text-xl"
            type="submit"
            name="install"
            disabled={selectedServerNames.length === 0}
          >
            Install
          </Button>
        </div>
      </form>
    </Form>
  );
};

export default ConfigurationForm;
