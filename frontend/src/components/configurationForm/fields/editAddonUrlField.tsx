import { FC, useState } from 'react';
import { UseFormReturn } from 'react-hook-form';
import { ConfigurationFormType } from '@/components/configurationForm/formSchema.tsx';
import { parseAddonUrl } from '@/components/configurationForm/utils.tsx';
import { Button } from '@/components/ui/button.tsx';
import {
  FormDescription,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form.tsx';
import { Input } from '@/components/ui/input.tsx';

interface Props {
  form: UseFormReturn<ConfigurationFormType>;
}

/**
 * Paste an existing addon install URL (or its base64 config) to load the
 * saved settings back into the form — legacy single-server configs are
 * migrated to the multi-server shape automatically.
 */
export const EditAddonUrlField: FC<Props> = ({ form }) => {
  const [value, setValue] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleLoad = () => {
    const parsed = parseAddonUrl(value);
    if (!parsed) {
      setError(
        'Could not parse this URL. Paste the full addon install link (…/manifest.json) or its base64 config.',
      );
      return;
    }
    setError(null);
    form.reset(parsed);
  };

  return (
    <FormItem className="rounded-lg border p-2">
      <FormLabel className="text-base">Edit an existing addon</FormLabel>
      <FormDescription>
        Paste an install link you already use to load its settings into this
        form, tweak them, and generate a fresh link.
      </FormDescription>
      <div className="flex items-center space-x-2">
        <Input
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            setError(null);
          }}
          placeholder="https://your-addon/…/manifest.json"
        />
        <Button
          type="button"
          variant="secondary"
          onClick={handleLoad}
          disabled={!value.trim()}
        >
          Load
        </Button>
      </div>
      {error && <FormMessage>{error}</FormMessage>}
    </FormItem>
  );
};
