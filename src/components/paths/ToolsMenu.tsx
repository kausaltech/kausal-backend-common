import { useState } from 'react';

import styled from '@emotion/styled';
import {
  IconButton,
  ListItemIcon,
  ListItemText,
  ListSubheader,
  Menu,
  MenuItem,
} from '@mui/material';
import { FiletypeCsv, FiletypeXls, ThreeDotsVertical } from 'react-bootstrap-icons';

import type { TFunction } from '@common/i18n';
import { type ParsedMetric, type SliceConfig, downloadData } from '@common/utils/paths/metric';

const Tools = styled.div`
  position: absolute;
  top: 0;
  right: 0;
  text-align: right;
  .btn-link {
    text-decoration: none;
  }
  .icon {
    width: 1.25rem !important;
    height: 1.25rem !important;
    vertical-align: -0.2rem;
  }
`;

type ToolsMenuProps = {
  cube: ParsedMetric;
  sliceConfig: SliceConfig;
  t: TFunction;
};

export default function ToolsMenu({ cube, sliceConfig, t }: ToolsMenuProps) {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const open = Boolean(anchorEl);

  const handleClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  return (
    <Tools>
      <IconButton
        id="tools-button"
        aria-controls={open ? 'tools-menu' : undefined}
        aria-haspopup="true"
        aria-expanded={open ? 'true' : undefined}
        onClick={handleClick}
        aria-label={t('download-data')}
      >
        <ThreeDotsVertical />
      </IconButton>
      <Menu
        id="tools-menu"
        anchorEl={anchorEl}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
        open={open}
        onClose={handleClose}
        slotProps={{ list: { 'aria-labelledby': 'tools-button' } }}
      >
        <ListSubheader>{` ${t('download-data')}`}</ListSubheader>
        <MenuItem onClick={() => void downloadData(cube, sliceConfig, 'xlsx')}>
          <ListItemIcon>
            <FiletypeXls />
          </ListItemIcon>
          <ListItemText>XLS</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => void downloadData(cube, sliceConfig, 'csv')}>
          <ListItemIcon>
            <FiletypeCsv />
          </ListItemIcon>
          <ListItemText>CSV</ListItemText>
        </MenuItem>
      </Menu>
    </Tools>
  );
}
