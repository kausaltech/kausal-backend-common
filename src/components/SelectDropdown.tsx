'use client';

import { useEffect, useState } from 'react';

import Autocomplete, { type AutocompleteRenderOptionState } from '@mui/material/Autocomplete';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import FormControl from '@mui/material/FormControl';
import FormLabel from '@mui/material/FormLabel';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import Highlighter from 'react-highlight-words';

import PopoverTip from '@common/components/PopoverTip';

export interface SelectDropdownOption {
  id: string;
  label: string;
  indent?: number;
}

type BaseProps = {
  id: string;
  label?: string;
  helpText?: string;
  invert?: boolean;
  className?: string;
  placeholder?: string;
  options: readonly SelectDropdownOption[];
  isClearable?: boolean;
};

type SingleProps = BaseProps & {
  isMulti: false;
  value: SelectDropdownOption | null;
  onChange: (option: SelectDropdownOption | null) => void;
};

type MultiProps = BaseProps & {
  isMulti: true;
  value: SelectDropdownOption[];
  onChange: (options: SelectDropdownOption[]) => void;
};

type SelectDropdownProps = SingleProps | MultiProps;

function renderOption(
  props: React.HTMLAttributes<HTMLLIElement>,
  option: SelectDropdownOption,
  state: AutocompleteRenderOptionState,
  isHierarchical: boolean
) {
  const { key, ...liProps } = props as typeof props & { key: string };
  const isPrimary = isHierarchical && (option.indent ?? 0) === 0;

  return (
    <li key={key} {...liProps}>
      <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
        {Array.from({ length: option.indent ?? 0 }).map((_, i) => (
          <Box
            key={i}
            sx={{ borderLeft: '2px solid', borderColor: 'grey.300', mr: 1.5, alignSelf: 'stretch' }}
          />
        ))}
        <Typography
          variant={isPrimary ? 'body2' : 'body2'}
          sx={{ fontWeight: isPrimary ? 'bold' : 'normal', py: 0.75 }}
        >
          <Highlighter
            highlightClassName="search-found"
            searchWords={[state.inputValue]}
            textToHighlight={option.label}
          />
        </Typography>
      </Box>
    </li>
  );
}

export default function SelectDropdown(props: SelectDropdownProps) {
  const { id, label, helpText, invert, className, placeholder, options, isClearable } = props;
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  const isHierarchical = options.some((o) => (o.indent ?? 0) > 0);

  // Label element with optional tooltip
  const labelLastWord = label?.split(' ').pop();
  const labelText = helpText ? label?.slice(0, label.length - (labelLastWord?.length ?? 0)) : label;
  const labelElement =
    label != null ? (
      <FormLabel htmlFor={id} sx={{ mb: 0.5, display: 'block' }}>
        {labelText}
        {helpText && (
          <Box component="span" sx={{ whiteSpace: 'nowrap' }}>
            {' '}
            {labelLastWord}
            <PopoverTip content={helpText} />
          </Box>
        )}
      </FormLabel>
    ) : null;

  if (!isClient) {
    return (
      <FormControl fullWidth className={className}>
        {labelElement}
      </FormControl>
    );
  }

  if (props.isMulti) {
    return (
      <FormControl fullWidth className={className}>
        {labelElement}
        <Autocomplete<SelectDropdownOption, true, false>
          multiple
          id={id}
          options={options}
          value={props.value}
          disableClearable={false}
          getOptionLabel={(option) => option.label}
          isOptionEqualToValue={(option, val) => option.id === val.id}
          renderOption={(liProps, option, state) =>
            renderOption(liProps, option, state, isHierarchical)
          }
          renderTags={(tagValues, getTagProps) => {
            if (tagValues.length === 0) return null;
            const [first, ...rest] = tagValues;
            const { key, ...tagProps } = getTagProps({ index: 0 });
            return (
              <>
                <Chip key={key} label={first.label} size="small" {...tagProps} />
                {rest.length > 0 && (
                  <Typography
                    component="span"
                    variant="body2"
                    sx={{ opacity: 0.5, fontStyle: 'italic', mx: 0.5 }}
                  >
                    +{rest.length}
                  </Typography>
                )}
              </>
            );
          }}
          onChange={(_event, newValue) => {
            props.onChange(newValue);
          }}
          renderInput={(params) => (
            <TextField
              {...params}
              size="small"
              placeholder={!props.value.length ? placeholder : undefined}
            />
          )}
        />
      </FormControl>
    );
  }

  return (
    <FormControl fullWidth className={className}>
      {labelElement}
      <Autocomplete<SelectDropdownOption, false, boolean>
        id={id}
        options={options}
        value={props.value}
        disableClearable={!isClearable as boolean}
        getOptionLabel={(option) => option.label}
        isOptionEqualToValue={(option, val) => option.id === val.id}
        renderOption={(liProps, option, state) =>
          renderOption(liProps, option, state, isHierarchical)
        }
        onChange={(_event, newValue) => {
          props.onChange(newValue);
        }}
        renderInput={(params) => <TextField {...params} size="small" placeholder={placeholder} />}
      />
    </FormControl>
  );
}
