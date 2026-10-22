/**
 * TagSection – renders tags for a document with add/remove functionality.
 */

"use client";

import { useEffect, useRef, useState } from "react";
import { useFrappeGetCall, useFrappePostCall } from "frappe-react-sdk";
import { Plus, Tags, X } from "lucide-react";

interface TagSectionProps {
  currentDoctype: string;
  currentName: string;
  initialTags: string[];
  reloadData?: () => void;
}

export function TagSection({
  currentDoctype,
  currentName,
  initialTags,
  reloadData,
}: TagSectionProps) {
  const [tags, setTags] = useState<string[]>([]);
  const [isTagInputOpen, setIsTagInputOpen] = useState(false);
  const [newTag, setNewTag] = useState("");
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const containerRef = useRef<HTMLDivElement>(null);

  const { call: addTagCall } = useFrappePostCall(
    "frappe.desk.doctype.tag.tag.add_tag",
  );
  const { call: removeTagCall } = useFrappePostCall(
    "frappe.desk.doctype.tag.tag.remove_tag",
  );
  const shouldFetchTags = isTagInputOpen && currentDoctype;
  const { data: suggestionData } = useFrappeGetCall(
    shouldFetchTags
      ? ("frappe.desk.doctype.tag.tag.get_tags" as const)
      : (null as any),
    shouldFetchTags ? ({ doctype: currentDoctype, txt: "" } as any) : null,
    shouldFetchTags ? `tag-suggestions-${currentDoctype}` : null,
  );

  useEffect(() => {
    setTags(initialTags || []);
  }, [initialTags]);
  useEffect(() => {
    if (isTagInputOpen && suggestionData?.message)
      setSuggestions(suggestionData.message);
    else if (!isTagInputOpen) setSuggestions([]);
  }, [suggestionData, isTagInputOpen]);
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        if (isTagInputOpen) handleSaveTag();
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isTagInputOpen, newTag]);

  const handleSaveTag = async (tagValue?: string) => {
    const cleanedTag = (tagValue ?? newTag).trim();
    if (!cleanedTag || !currentDoctype || !currentName) {
      setIsTagInputOpen(false);
      setNewTag("");
      return;
    }
    if (tags.includes(cleanedTag)) {
      setIsTagInputOpen(false);
      setNewTag("");
      return;
    }
    try {
      await addTagCall({
        tag: cleanedTag,
        dt: currentDoctype,
        dn: currentName,
      });
      setTags((prev) => [...new Set([...prev, cleanedTag])]);
      setNewTag("");
      setIsTagInputOpen(false);
      reloadData?.();
    } catch (err) {
      console.error(err);
    }
  };

  const handleRemoveTag = async (tagToRemove: string) => {
    if (!currentDoctype || !currentName) return;
    try {
      await removeTagCall({
        tag: tagToRemove,
        dt: currentDoctype,
        dn: currentName,
      });
      setTags((prev) => prev.filter((t) => t !== tagToRemove));
      reloadData?.();
    } catch (err) {
      console.error(err);
    }
  };

  const filteredSuggestions = suggestions.filter(
    (s) => s.toLowerCase().includes(newTag.toLowerCase()) && !tags.includes(s),
  );
  const showCustomOption =
    newTag.trim() &&
    !tags.includes(newTag.trim()) &&
    !suggestions.some(
      (s) => s.toLowerCase() === newTag.trim().toLowerCase(),
    );

  return (
    <div ref={containerRef} className="relative">
      <div className="flex items-center justify-between text-muted-foreground py-1">
        <span className="flex items-center gap-2 font-bold uppercase tracking-wider text-[10px] text-muted-foreground">
          <Tags className="w-3.5 h-3.5" /> Tags
        </span>
        <button
          onClick={() => setIsTagInputOpen(!isTagInputOpen)}
          className="hover:text-foreground p-0.5"
        >
          <Plus className="w-3 h-3" />
        </button>
      </div>
      {isTagInputOpen && (
        <div className="mt-2 relative z-10">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSaveTag();
            }}
            className="flex gap-1.5"
          >
            <input
              type="text"
              value={newTag}
              onChange={(e) => setNewTag(e.target.value)}
              placeholder="Add or search tag..."
              className="flex-1 p-1 px-2 border border-input rounded-md focus:outline-none focus:ring-1 focus:ring-primary text-xs bg-background"
              autoFocus
            />
          </form>
          {(filteredSuggestions.length > 0 || showCustomOption) && (
            <div className="absolute left-0 right-0 mt-1 max-h-32 overflow-y-auto bg-card border border-border rounded-md shadow-lg">
              {filteredSuggestions.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => handleSaveTag(suggestion)}
                  className="w-full text-left px-2 py-1 text-xs text-foreground hover:bg-muted transition-colors"
                >
                  {suggestion}
                </button>
              ))}
              {showCustomOption && (
                <button
                  type="button"
                  onClick={() => handleSaveTag(newTag)}
                  className="w-full text-left px-2 py-1 text-xs text-primary font-medium hover:bg-muted transition-colors border-t border-border"
                >
                  Add "{newTag.trim()}"
                </button>
              )}
            </div>
          )}
        </div>
      )}
      <div className="mt-2 flex flex-wrap gap-1.5">
        {tags.map((tag) => {
          const bgColors = [
            "bg-emerald-50 text-emerald-700 border-emerald-100",
            "bg-purple-50 text-purple-700 border-purple-100",
            "bg-orange-50 text-orange-700 border-orange-100",
          ];
          const pickedColor =
            bgColors[Math.abs(tag.charCodeAt(0) || 0) % bgColors.length];
          return (
            <span
              key={tag}
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[11px] font-medium ${pickedColor}`}
            >
              {tag}
              <button
                onClick={() => handleRemoveTag(tag)}
                className="hover:opacity-70"
              >
                <X className="w-2.5 h-2.5" />
              </button>
            </span>
          );
        })}
      </div>
    </div>
  );
}

export default TagSection;