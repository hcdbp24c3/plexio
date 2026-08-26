import { FC } from 'react';
import { UseFormReturn } from 'react-hook-form';
import { ConfigurationFormType } from '@/components/configurationForm/formSchema.tsx';
import { Badge } from '@/components/ui/badge.tsx';
import { Checkbox } from '@/components/ui/checkbox.tsx';
import {
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form.tsx';
import { PlexServer } from '@/types/plex.tsx';

interface Props {
  form: UseFormReturn<ConfigurationFormType>;
  servers: PlexServer[];
  onSelectionChange: (selectedNames: string[]) => void;
}

export const ServerCheckboxListField: FC<Props> = ({
  form,
  servers,
  onSelectionChange,
}) => {
  return (
    <FormField
      control={form.control}
      name="selectedServers"
      render={() => (
        <FormItem className="rounded-lg border p-2">
          <div className="mb-4">
            <FormLabel className="text-base">Plex Servers</FormLabel>
            <FormDescription>
              Select one or more Plex servers to configure.
            </FormDescription>
          </div>
          {servers.map((server) => (
            <FormField
              key={server.name}
              control={form.control}
              name="selectedServers"
              render={({ field }) => {
                const checked = field.value?.includes(server.name);
                return (
                  <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                    <FormControl>
                      <Checkbox
                        checked={checked}
                        onCheckedChange={(isChecked) => {
                          const newValue = isChecked
                            ? [...(field.value || []), server.name]
                            : (field.value || []).filter(
                                (name) => name !== server.name,
                              );
                          field.onChange(newValue);
                          onSelectionChange(newValue);
                        }}
                      />
                    </FormControl>
                    <FormLabel className="font-normal">
                      {!server.owned && (
                        <Badge className="mr-1.5" variant="secondary">
                          shared
                        </Badge>
                      )}
                      {server.name}
                    </FormLabel>
                  </FormItem>
                );
              }}
            />
          ))}
          <FormMessage />
        </FormItem>
      )}
    />
  );
};
