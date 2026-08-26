import { FC, useState } from 'react';
import { UseFormReturn } from 'react-hook-form';
import { ConfigurationFormType } from '@/components/configurationForm/formSchema.tsx';
import { parseUrlToIpPort } from '@/components/configurationForm/utils.tsx';
import { Badge } from '@/components/ui/badge.tsx';
import { Button } from '@/components/ui/button.tsx';
import { Checkbox } from '@/components/ui/checkbox.tsx';
import {
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form.tsx';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select.tsx';
import usePMSSections from '@/hooks/usePMSSections.tsx';
import { useToast } from '@/hooks/useToast';
import { isServerAliveLocal } from '@/services/PMSService.tsx';
import { isServerAliveRemote } from '@/services/BackendService.tsx';
import { PlexServer } from '@/types/plex.tsx';

interface Props {
  form: UseFormReturn<ConfigurationFormType>;
  server: PlexServer;
  index: number;
}

export const PerServerConfig: FC<Props> = ({ form, server, index }) => {
  const { toast } = useToast();
  const prefix = `serverConfigs.${index}` as const;

  const discoveryUrl = form.watch(
    `${prefix}.discoveryUrl` as never,
  ) as unknown as string;
  const sections = usePMSSections(discoveryUrl, server.accessToken);

  const [testDiscoveryInProgress, setTestDiscoveryInProgress] =
    useState(false);
  const [testStreamingInProgress, setTestStreamingInProgress] =
    useState(false);

  const testDiscoveryUrl = () => {
    setTestDiscoveryInProgress(true);
    void isServerAliveRemote(discoveryUrl, server.accessToken).then(
      (alive) => {
        setTestDiscoveryInProgress(false);
        const ipPort = parseUrlToIpPort(discoveryUrl);
        if (alive) {
          toast({
            title: 'Discovery URL Test Successful!',
            description: `Plexio backend successfully accessed your server at ${ipPort}.`,
            variant: 'success',
            duration: 30 * 1000,
          });
        } else {
          toast({
            title: 'Discovery URL Test Failed!',
            description: `Plexio backend could not access your server at ${ipPort}. 
                        Please try again or select another URL. Ensure your server is accessible publicly, 
                        or consider using Plex Relay if the server is behind a firewall.`,
            variant: 'destructive',
            duration: 30 * 1000,
          });
        }
      },
    );
  };

  const streamingUrl = form.watch(
    `${prefix}.streamingUrl` as never,
  ) as unknown as string;

  const testStreamingUrl = () => {
    setTestStreamingInProgress(true);
    void isServerAliveLocal(streamingUrl, server.accessToken).then(
      (alive) => {
        setTestStreamingInProgress(false);
        const ipPort = parseUrlToIpPort(streamingUrl);
        if (alive) {
          toast({
            title: 'Streaming URL Test Successful!',
            description: `Your device successfully accessed the Streaming URL at ${ipPort}.
                        Streaming will work if accessed from this device.`,
            variant: 'success',
            duration: 30 * 1000,
          });
        } else {
          toast({
            title: 'Streaming URL Test Failed!',
            description: `Your device could not access the Streaming URL at ${ipPort}. 
                        If you plan to stream from a different device, this may be expected behavior. 
                        Otherwise, please try again or select another URL. 
                        If your server is behind a firewall, consider using Plex Relay.`,
            variant: 'destructive',
            duration: 30 * 1000,
          });
        }
      },
    );
  };

  return (
    <div className="rounded-lg border p-3 space-y-2">
      <div className="flex items-center gap-2 mb-2">
        <h3 className="text-base font-semibold">{server.name}</h3>
        {!server.owned && <Badge variant="secondary">shared</Badge>}
      </div>

      {/* Discovery URL */}
      <FormField
        control={form.control}
        name={`${prefix}.discoveryUrl` as never}
        render={({ field }) => (
          <FormItem className="rounded-lg border p-2">
            <FormLabel className="text-base">Discovery URL</FormLabel>
            <div className="flex">
              <Select
                onValueChange={field.onChange}
                defaultValue=""
                value={field.value as string}
              >
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a discovery url" />
                  </SelectTrigger>
                </FormControl>
                {server.connections.filter((conn) => !conn.local).length >
                  0 && (
                  <SelectContent>
                    {server.connections
                      .filter((conn) => !conn.local)
                      .map((conn, i) => (
                        <SelectItem key={i} value={conn.uri}>
                          {conn.relay && (
                            <Badge className="mr-1.5" variant="secondary">
                              relay
                            </Badge>
                          )}
                          {`${conn.address}:${conn.port}`}
                        </SelectItem>
                      ))}
                  </SelectContent>
                )}
              </Select>
              <Button
                className="ml-2.5 h-10 w-16"
                type="button"
                disabled={testDiscoveryInProgress || !discoveryUrl}
                onClick={testDiscoveryUrl}
              >
                {testDiscoveryInProgress ? (
                  <div className="w-5 h-5 rounded-full animate-spin border-t-2" />
                ) : (
                  'Test'
                )}
              </Button>
            </div>
            <FormDescription>
              Select the public URL of your Plex server.
            </FormDescription>
            <FormMessage />
          </FormItem>
        )}
      />

      {/* Streaming URL */}
      <FormField
        control={form.control}
        name={`${prefix}.streamingUrl` as never}
        render={({ field }) => (
          <FormItem className="rounded-lg border p-2">
            <FormLabel className="text-base">Streaming URL</FormLabel>
            <div className="flex">
              <Select
                onValueChange={field.onChange}
                defaultValue=""
                value={field.value as string}
              >
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a streaming url" />
                  </SelectTrigger>
                </FormControl>
                {server.connections.length > 0 && (
                  <SelectContent>
                    {server.connections.map((conn, i) => (
                      <SelectItem key={i} value={conn.uri}>
                        {conn.local && (
                          <Badge className="mr-1.5" variant="secondary">
                            local
                          </Badge>
                        )}
                        {conn.relay && (
                          <Badge className="mr-1.5" variant="secondary">
                            relay
                          </Badge>
                        )}
                        {`${conn.address}:${conn.port}`}
                      </SelectItem>
                    ))}
                  </SelectContent>
                )}
              </Select>
              <Button
                className="ml-2.5 h-10 w-16"
                type="button"
                disabled={testStreamingInProgress || !streamingUrl}
                onClick={testStreamingUrl}
              >
                {testStreamingInProgress ? (
                  <div className="w-5 h-5 rounded-full animate-spin border-t-2" />
                ) : (
                  'Test'
                )}
              </Button>
            </div>
            <FormDescription>
              Select the URL of your Plex server for streaming content to
              Stremio clients.
            </FormDescription>
            <FormMessage />
          </FormItem>
        )}
      />

      {/* Sections */}
      <FormField
        control={form.control}
        name={`${prefix}.sections` as never}
        render={() => (
          <FormItem className="rounded-lg border p-2">
            <div className="mb-4">
              <FormLabel className="text-base">Sections</FormLabel>
              <FormDescription>
                Select the Plex library sections to access in Stremio.
              </FormDescription>
            </div>
            {sections.length > 0 ? (
              sections.map((item: { key: string; title: string; type: string }) => (
                <FormField
                  key={item.key}
                  control={form.control}
                  name={`${prefix}.sections` as never}
                  render={({ field }) => {
                    const fieldValue = (field.value ?? []) as {
                      key: string;
                      title: string;
                      type: string;
                    }[];
                    return (
                      <FormItem
                        key={item.key}
                        className="flex flex-row items-start space-x-3 space-y-0"
                      >
                        <FormControl>
                          <Checkbox
                            checked={fieldValue.some(
                              (v) => v.key === item.key,
                            )}
                            onCheckedChange={(checked) => {
                              return checked
                                ? field.onChange([
                                    ...fieldValue,
                                    {
                                      key: item.key,
                                      title: item.title,
                                      type: item.type,
                                    },
                                  ])
                                : field.onChange(
                                    fieldValue.filter(
                                      (value) => value.key !== item.key,
                                    ),
                                  );
                            }}
                          />
                        </FormControl>
                        <FormLabel className="font-normal">
                          {item.title}
                        </FormLabel>
                      </FormItem>
                    );
                  }}
                />
              ))
            ) : (
              <div className="flex flex-col items-center justify-center">
                <div className="w-16 h-16 rounded-full animate-spin border-t-4 border-muted-foreground" />
                <span className="mt-4 text-lg text-muted-foreground text-center">
                  Loading sections from the server using the selected discovery
                  URL.
                  <br />
                  If this takes too long, try selecting a different discovery
                  URL.
                </span>
              </div>
            )}
            <FormMessage />
          </FormItem>
        )}
      />
    </div>
  );
};
