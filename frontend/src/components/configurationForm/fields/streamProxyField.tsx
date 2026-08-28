import { FC } from 'react';
import { UseFormReturn } from 'react-hook-form';
import { ConfigurationFormType } from '@/components/configurationForm/formSchema.tsx';
import {
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
} from '@/components/ui/form.tsx';
import { Switch } from '@/components/ui/switch.tsx';

interface Props {
  form: UseFormReturn<ConfigurationFormType>;
}

export const StreamProxyField: FC<Props> = ({ form }) => {
  return (
    <FormField
      control={form.control}
      name="streamProxy"
      render={({ field }) => (
        <FormItem className="items-center justify-between flex flex-row rounded-lg border p-2">
          <div className="space-y-0.5">
            <FormLabel className="text-base">Proxy streams</FormLabel>
            <FormDescription>
              Relay media and posters through this addon so Stremio players
              never see your Plex server address or access token. Uses addon
              bandwidth, so only enable it when you need the extra privacy.
            </FormDescription>
          </div>
          <FormControl>
            <Switch checked={field.value} onCheckedChange={field.onChange} />
          </FormControl>
        </FormItem>
      )}
    />
  );
};
