# Virtualized DataTable (React + TypeScript)

A production-ready virtualized data table component using `@tanstack/react-virtual` with full accessibility support.

```tsx
import React, { memo, useCallback } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';

interface Column {
  key: string;
  label: string;
  width?: number;
}

interface DataTableProps {
  data: Array<Record<string, any>>;
  columns: Column[];
  onRowClick?: (row: Record<string, any>) => void;
}

export const DataTable = memo<DataTableProps>(({ data, columns, onRowClick }) => {
  const parentRef = React.useRef<HTMLDivElement>(null);

  const rowVirtualizer = useVirtualizer({
    count: data.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 50,
    overscan: 5,
  });

  const handleRowClick = useCallback((row: Record<string, any>) => {
    onRowClick?.(row);
  }, [onRowClick]);

  return (
    <div
      ref={parentRef}
      className="h-96 overflow-auto"
      role="table"
      aria-label="Data table"
    >
      <div role="row" className="flex font-semibold border-b bg-gray-100 sticky top-0">
        {columns.map((column) => (
          <div key={column.key} className="px-4 py-2 flex-1" role="columnheader">
            {column.label}
          </div>
        ))}
      </div>
      <div
        style={{ height: `${rowVirtualizer.getTotalSize()}px`, position: 'relative' }}
      >
        {rowVirtualizer.getVirtualItems().map((virtualItem) => {
          const row = data[virtualItem.index];
          return (
            <div
              key={virtualItem.key}
              className="flex items-center border-b hover:bg-gray-50 cursor-pointer absolute w-full"
              style={{ height: `${virtualItem.size}px`, top: `${virtualItem.start}px` }}
              onClick={() => handleRowClick(row)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleRowClick(row); }}
              role="row"
              tabIndex={0}
            >
              {columns.map((column) => (
                <div key={column.key} className="px-4 py-2 flex-1" role="cell">
                  {row[column.key]}
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
});

DataTable.displayName = 'DataTable';
```
